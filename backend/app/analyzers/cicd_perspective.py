"""CI/CD perspective analyzer — filters for pipeline entities and builds a DAG."""

from app.analyzers.base import PerspectiveAnalyzer
from app.models.domain import CodeEntity, DiagramData, FlowNode, Relationship
from app.utils.determinism import canonical_sort_entities, canonical_sort_relationships

_PIPELINE_TYPES = {"pipeline_stage", "pipeline_job", "pipeline_trigger"}
_PIPELINE_REL_TYPES = {"triggers", "depends_on", "contains"}


class CICDPerspectiveAnalyzer(PerspectiveAnalyzer):
    """Filters for pipeline_* entity types and builds FlowNodes for the pipeline DAG."""

    @property
    def perspective_name(self) -> str:
        return "cicd"

    def analyze(
        self,
        entities: list[CodeEntity],
        relationships: list[Relationship],
    ) -> DiagramData:
        pipeline_entities = [e for e in entities if e.entity_type in _PIPELINE_TYPES]
        pipeline_ids = {e.id for e in pipeline_entities}

        pipeline_rels = [
            r for r in relationships
            if r.relationship_type in _PIPELINE_REL_TYPES
            and r.source_id in pipeline_ids
            and r.target_id in pipeline_ids
        ]

        # Build forward adjacency for flow nodes
        forward: dict[str, list[str]] = {}
        for r in pipeline_rels:
            forward.setdefault(r.source_id, []).append(r.target_id)

        flow_nodes: list[FlowNode] = []
        for entity in pipeline_entities:
            connections = sorted(forward.get(entity.id, []))
            flow_nodes.append(FlowNode(
                id=entity.id,
                label=entity.name,
                node_type=entity.entity_type,
                connections=connections,
            ))

        flow_nodes.sort(key=lambda n: n.id)

        return DiagramData(
            entities=canonical_sort_entities(pipeline_entities),
            relationships=canonical_sort_relationships(pipeline_rels),
            flow_nodes=flow_nodes,
            metadata={"perspective": self.perspective_name},
        )
