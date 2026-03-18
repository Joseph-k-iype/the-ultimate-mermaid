"""FalkorDB-backed knowledge graph service with graceful fallback."""

from __future__ import annotations

import logging
from typing import Any

from app.graph.ontology import (
    CONCEPT_HIERARCHY,
    ENTITY_TO_CONCEPT,
    PERSPECTIVE_DEFINITIONS,
)
from app.models.domain import CodeEntity, DiagramData, FlowNode, Relationship
from app.models.pattern import PatternModel, PatternStatus

logger = logging.getLogger(__name__)


class GraphService:
    """Singleton graph service. Falls back to no-op when FalkorDB is unavailable."""

    def __init__(self) -> None:
        self._available = False
        self._graph: Any = None
        self._db: Any = None

    def connect(self, host: str, port: int, graph_name: str) -> None:
        """Attempt connection to FalkorDB. Sets _available on success."""
        try:
            from falkordb import FalkorDB

            self._db = FalkorDB(host=host, port=port)
            self._graph = self._db.select_graph(graph_name)
            # Test connectivity
            self._graph.query("RETURN 1")
            self._available = True
            logger.info("FalkorDB connected at %s:%s graph=%s", host, port, graph_name)
        except Exception as exc:
            self._available = False
            self._graph = None
            self._db = None
            logger.info("FalkorDB not available (%s), using fallback mode", exc)

    @property
    def is_available(self) -> bool:
        return self._available

    def _query(self, cypher: str, params: dict | None = None) -> Any:
        """Execute a Cypher query. Returns result set or None."""
        if not self._available or self._graph is None:
            return None
        try:
            return self._graph.query(cypher, params or {})
        except Exception as exc:
            logger.warning("Graph query failed: %s", exc)
            return None

    # --- Schema initialization ---

    def initialize_schema(self) -> None:
        """Create indexes and SKOS Concept nodes with BROADER/NARROWER edges."""
        if not self._available:
            return

        # Create indexes (FalkorDB syntax)
        for label in ("CodeEntity", "Scan", "Pattern", "Concept"):
            self._query(f"CREATE INDEX FOR (n:{label}) ON (n.id)")

        # Create concept hierarchy nodes and edges
        for broader, narrower_list in CONCEPT_HIERARCHY.items():
            self._query(
                "MERGE (c:Concept {name: $name, level: 'broader'})",
                {"name": broader},
            )
            for narrower in narrower_list:
                self._query(
                    "MERGE (n:Concept {name: $narrower, level: 'narrower'}) "
                    "WITH n "
                    "MATCH (b:Concept {name: $broader}) "
                    "MERGE (n)-[:BROADER]->(b) "
                    "MERGE (b)-[:NARROWER]->(n)",
                    {"narrower": narrower, "broader": broader},
                )

        logger.info("Graph schema initialized")

    def clear_all(self) -> None:
        """Delete all nodes and edges, then re-initialize schema."""
        if not self._available:
            return
        # Drop everything
        self._query("MATCH (n) DETACH DELETE n")
        logger.info("Cleared all graph data")
        # Recreate the schema (indexes + Concept hierarchy)
        self.initialize_schema()

    # --- Entity / Relationship storage ---

    def store_entities(self, scan_id: str, entities: list[CodeEntity]) -> None:
        """Store entities as graph nodes linked to a Scan node."""
        if not self._available:
            return

        self._query(
            "MERGE (s:Scan {id: $scan_id})",
            {"scan_id": scan_id},
        )

        for entity in entities:
            concept_name = ENTITY_TO_CONCEPT.get(entity.entity_type)
            self._query(
                "MERGE (e:CodeEntity {id: $id}) "
                "SET e.name = $name, e.entity_type = $entity_type, "
                "e.file_path = $file_path, e.line_number = $line_number, "
                "e.component = $component "
                "WITH e "
                "MATCH (s:Scan {id: $scan_id}) "
                "MERGE (e)-[:BELONGS_TO_SCAN]->(s)",
                {
                    "id": entity.id,
                    "name": entity.name,
                    "entity_type": entity.entity_type,
                    "file_path": entity.file_path,
                    "line_number": entity.line_number,
                    "component": entity.metadata.get("component", ""),
                    "scan_id": scan_id,
                },
            )

            if concept_name:
                self._query(
                    "MATCH (e:CodeEntity {id: $id}) "
                    "MATCH (c:Concept {name: $concept}) "
                    "MERGE (e)-[:HAS_TAG]->(c)",
                    {"id": entity.id, "concept": concept_name},
                )

    def store_relationships(self, relationships: list[Relationship]) -> None:
        """Store typed edges between CodeEntity nodes."""
        if not self._available:
            return

        for rel in relationships:
            rel_type = rel.relationship_type.upper()
            self._query(
                f"MATCH (a:CodeEntity {{id: $src}}) "
                f"MATCH (b:CodeEntity {{id: $tgt}}) "
                f"MERGE (a)-[:{rel_type}]->(b)",
                {"src": rel.source_id, "tgt": rel.target_id},
            )

    # --- Pattern storage ---

    def store_pattern(self, pattern: PatternModel) -> None:
        """Create a Pattern node with tag edges to Concept nodes."""
        if not self._available:
            return

        self._query(
            "MERGE (p:Pattern {id: $id}) "
            "SET p.title = $title, p.description = $desc, "
            "p.owner = $owner, p.status = $status, p.version = $version",
            {
                "id": pattern.id,
                "title": pattern.title,
                "desc": pattern.description,
                "owner": pattern.owner,
                "status": pattern.status.value,
                "version": pattern.version,
            },
        )

        # Link tags to concept nodes
        for tag in pattern.tags:
            self._query(
                "MATCH (p:Pattern {id: $id}) "
                "MATCH (c:Concept {name: $tag}) "
                "MERGE (p)-[:HAS_TAG]->(c)",
                {"id": pattern.id, "tag": tag},
            )

        # Link to scan if applicable
        if pattern.linked_scan_id:
            self._query(
                "MATCH (p:Pattern {id: $pid}) "
                "MATCH (s:Scan {id: $sid}) "
                "MERGE (p)-[:LINKED_TO_PATTERN]->(s)",
                {"pid": pattern.id, "sid": pattern.linked_scan_id},
            )

    def update_pattern(self, pattern_id: str, updates: dict) -> None:
        """Update Pattern node properties. Rebuild tag edges if tags changed."""
        if not self._available:
            return

        set_parts = []
        params: dict[str, Any] = {"id": pattern_id}
        for key in ("title", "description", "owner", "status", "version"):
            if key in updates:
                set_parts.append(f"p.{key} = ${key}")
                params[key] = updates[key]

        if set_parts:
            self._query(
                f"MATCH (p:Pattern {{id: $id}}) SET {', '.join(set_parts)}",
                params,
            )

        if "tags" in updates:
            # Remove old tag edges
            self._query(
                "MATCH (p:Pattern {id: $id})-[r:HAS_TAG]->() DELETE r",
                {"id": pattern_id},
            )
            for tag in updates["tags"]:
                self._query(
                    "MATCH (p:Pattern {id: $id}) "
                    "MATCH (c:Concept {name: $tag}) "
                    "MERGE (p)-[:HAS_TAG]->(c)",
                    {"id": pattern_id, "tag": tag},
                )

    def delete_pattern(self, pattern_id: str) -> None:
        """Detach delete a Pattern node."""
        if not self._available:
            return
        self._query(
            "MATCH (p:Pattern {id: $id}) DETACH DELETE p",
            {"id": pattern_id},
        )

    # --- Perspective queries ---

    def query_perspective(self, scan_id: str, perspective: str) -> DiagramData | None:
        """Use PerspectiveDefinition to query the graph for a filtered view."""
        if not self._available:
            return None

        defn = PERSPECTIVE_DEFINITIONS.get(perspective)
        if defn is None:
            return None

        # Get entities matching perspective types for this scan
        entity_result = self._query(
            "MATCH (e:CodeEntity)-[:BELONGS_TO_SCAN]->(s:Scan {id: $scan_id}) "
            "WHERE e.entity_type IN $entity_types "
            "RETURN e.id, e.name, e.entity_type, e.file_path, e.line_number, e.component", # Added e.component
            {"scan_id": scan_id, "entity_types": defn.entity_types},
        )

        if entity_result is None:
            return None

        entities: list[CodeEntity] = []
        entity_ids: set[str] = set()
        for row in entity_result.result_set:
            eid, name, etype, fpath, line, comp = row
            entities.append(CodeEntity(
                id=eid, name=name, entity_type=etype,
                file_path=fpath, line_number=line,
                metadata={"component": comp} if comp else {}
            ))
            entity_ids.add(eid)

        # Get relationships between these entities
        rel_types_upper = [rt.upper() for rt in defn.relationship_types]
        rel_result = self._query(
            "MATCH (a:CodeEntity)-[r]->(b:CodeEntity) "
            "WHERE a.id IN $ids AND b.id IN $ids AND type(r) IN $rel_types "
            "RETURN a.id, b.id, type(r)",
            {"ids": list(entity_ids), "rel_types": rel_types_upper},
        )

        relationships: list[Relationship] = []
        rel_lookup: dict[str, list[str]] = {}
        if rel_result is not None:
            for row in rel_result.result_set:
                src, tgt, rtype = row
                relationships.append(Relationship(
                    source_id=src, target_id=tgt,
                    relationship_type=rtype.lower(),
                ))
                rel_lookup.setdefault(src, []).append(tgt)

        # Build flow nodes
        flow_nodes = []
        for entity in entities:
            connections = sorted(rel_lookup.get(entity.id, []))
            flow_nodes.append(FlowNode(
                id=entity.id, label=entity.name,
                node_type=entity.entity_type, connections=connections,
            ))
        flow_nodes.sort(key=lambda n: n.id)

        return DiagramData(
            entities=sorted(entities, key=lambda e: e.id),
            relationships=sorted(
                relationships, key=lambda r: (r.source_id, r.target_id)
            ),
            flow_nodes=flow_nodes,
            metadata={"perspective": perspective},
        )

    # --- Pattern search with SKOS traversal ---

    def search_patterns(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        status: PatternStatus | None = None,
        owner: str | None = None,
    ) -> list[dict] | None:
        """Graph search with SKOS concept traversal for tags."""
        if not self._available:
            return None

        conditions = []
        params: dict[str, Any] = {}

        if query:
            conditions.append(
                "(toLower(p.title) CONTAINS toLower($query) "
                "OR toLower(p.description) CONTAINS toLower($query))"
            )
            params["query"] = query

        if status:
            conditions.append("p.status = $status")
            params["status"] = status.value

        if owner:
            conditions.append("p.owner = $owner")
            params["owner"] = owner

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        if tags:
            # SKOS traversal: find patterns tagged with the given concepts
            # or concepts that are narrower (more specific) than the given ones
            params["tags"] = tags
            cypher = (
                f"MATCH (p:Pattern)-[:HAS_TAG]->(c:Concept)"
                f"-[:BROADER*0..2]->(broader:Concept) "
                f"{where_clause + ' AND ' if where_clause else 'WHERE '}"
                f"broader.name IN $tags OR c.name IN $tags "
                f"RETURN DISTINCT p.id, p.title, p.description, p.owner, "
                f"p.status, p.version"
            )
        else:
            cypher = (
                f"MATCH (p:Pattern) {where_clause} "
                f"RETURN p.id, p.title, p.description, p.owner, "
                f"p.status, p.version"
            )

        result = self._query(cypher, params)
        if result is None:
            return None

        patterns = []
        for row in result.result_set:
            pid, title, desc, powner, pstatus, version = row
            patterns.append({
                "id": pid,
                "title": title,
                "description": desc,
                "owner": powner,
                "status": pstatus,
                "version": version,
            })
        return patterns

    def find_related_patterns(self, pattern_id: str) -> list[dict]:
        """Find patterns sharing tags, linked to same scan, or same entities."""
        if not self._available:
            return []

        result = self._query(
            "MATCH (p:Pattern {id: $id})-[:HAS_TAG]->(c:Concept)"
            "<-[:HAS_TAG]-(other:Pattern) "
            "WHERE other.id <> $id "
            "RETURN DISTINCT other.id, other.title, other.description, "
            "other.owner, other.status, other.version "
            "LIMIT 10",
            {"id": pattern_id},
        )

        if result is None:
            return []

        patterns = []
        for row in result.result_set:
            pid, title, desc, owner, status, version = row
            patterns.append({
                "id": pid,
                "title": title,
                "description": desc,
                "owner": owner,
                "status": status,
                "version": version,
            })
        return patterns

    # --- Knowledge graph visualization ---

    def get_knowledge_graph(self, scan_id: str) -> dict:
        """Returns {nodes, edges} for a specific scan. Caps at 500 nodes."""
        if not self._available:
            return {"nodes": [], "edges": []}

        node_result = self._query(
            "MATCH (e:CodeEntity)-[:BELONGS_TO_SCAN]->(s:Scan {id: $scan_id}) "
            "RETURN e.id, e.name, e.entity_type, 'CodeEntity' AS label "
            "LIMIT 500",
            {"scan_id": scan_id},
        )

        nodes = []
        if node_result is not None:
            for row in node_result.result_set:
                nid, name, ntype, label = row
                nodes.append({
                    "id": nid,
                    "label": name or nid,
                    "type": label,
                    "properties": {"entity_type": ntype},
                })

        node_ids = [n["id"] for n in nodes]
        edges = []

        if node_ids:
            edge_result = self._query(
                "MATCH (a)-[r]->(b) "
                "WHERE a.id IN $ids AND b.id IN $ids "
                "RETURN a.id, b.id, type(r) "
                "LIMIT 2000",
                {"ids": node_ids},
            )
            if edge_result is not None:
                for row in edge_result.result_set:
                    src, tgt, rtype = row
                    edges.append({
                        "source": src,
                        "target": tgt,
                        "type": rtype,
                        "properties": {},
                    })

        return {"nodes": nodes, "edges": edges}

    def get_concepts(self) -> list[dict]:
        """Return the SKOS concept hierarchy."""
        concepts = []
        for broader_name, narrower_list in CONCEPT_HIERARCHY.items():
            concepts.append({
                "id": broader_name,
                "label": broader_name,
                "broader": None,
                "narrower": narrower_list,
            })
            for narrower_name in narrower_list:
                concepts.append({
                    "id": narrower_name,
                    "label": narrower_name,
                    "broader": broader_name,
                    "narrower": [],
                })
        return concepts

    def get_stats(self) -> dict:
        """Node counts by label, edge counts by type."""
        if not self._available:
            return {"nodes": {}, "edges": {}, "total_nodes": 0, "total_edges": 0}

        stats: dict[str, Any] = {"nodes": {}, "edges": {}}

        for label in ("CodeEntity", "Scan", "Pattern", "Concept"):
            result = self._query(f"MATCH (n:{label}) RETURN count(n)")
            if result and result.result_set:
                stats["nodes"][label] = result.result_set[0][0]
            else:
                stats["nodes"][label] = 0

        # Edge counts
        result = self._query(
            "MATCH ()-[r]->() RETURN type(r), count(r)"
        )
        if result is not None:
            for row in result.result_set:
                rtype, count = row
                stats["edges"][rtype] = count

        stats["total_nodes"] = sum(stats["nodes"].values())
        stats["total_edges"] = sum(stats["edges"].values())
        return stats


# Module-level singleton (lazy connect in main.py lifespan)
graph_service = GraphService()
