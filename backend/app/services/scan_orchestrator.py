from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.analyzers.component_detector import detect_components
from app.analyzers.dataflow_analyzer import DataFlowAnalyzer
from app.analyzers.er_analyzer import ERAnalyzer
from app.analyzers.manifest_analyzer import ManifestAnalyzer
from app.analyzers.registry import default_registry
from app.generators.dataflow_generator import DataFlowMermaidGenerator
from app.generators.er_generator import ERMermaidGenerator
from app.generators.manifest_generator import ManifestMermaidGenerator
from app.models.domain import CodeEntity, DiagramData, Relationship
from app.models.responses import DiagramResponse, ScanResponse
from app.services.repo_service import RepoService
from app.utils.determinism import generate_scan_id

# Pipeline order matters: manifest → er → dataflow.
# Each stage builds on the previous conceptually:
#   manifest = what data exists (inventory)
#   er       = how data entities relate structurally
#   dataflow = how data moves end-to-end
ALL_PERSPECTIVES = ("manifest", "er", "dataflow")
DEFAULT_PERSPECTIVES = ALL_PERSPECTIVES

# Keep old name for backward compatibility in imports
PERSPECTIVES = ALL_PERSPECTIVES

_PERSPECTIVE_ANALYZERS = {
    "manifest": ManifestAnalyzer(),
    "er": ERAnalyzer(),
    "dataflow": DataFlowAnalyzer(),
}

_MERMAID_GENERATORS = {
    "manifest": ManifestMermaidGenerator(),
    "er": ERMermaidGenerator(),
    "dataflow": DataFlowMermaidGenerator(),
}


@dataclass
class ScanState:
    scan_id: str
    status: str
    repo_url: str
    branch: str
    created_at: datetime
    entities: list[CodeEntity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    diagram_data: dict[str, DiagramData] = field(default_factory=dict)
    mermaid_code: dict[str, str] = field(default_factory=dict)
    requested_perspectives: list[str] = field(default_factory=list)
    components: dict[str, list[str]] = field(default_factory=dict)


class ScanOrchestrator:
    """Orchestrates the full scan pipeline: clone -> analyze -> generate diagrams."""

    def __init__(self) -> None:
        self._scans: dict[str, ScanState] = {}
        self._repo_service = RepoService()

    def start_scan(
        self, repo_url: str, branch: str, perspectives: list[str] | None = None
    ) -> ScanResponse:
        scan_id = generate_scan_id(repo_url, branch)
        now = datetime.now(timezone.utc)

        # Validate and default perspectives
        requested = list(perspectives) if perspectives else list(DEFAULT_PERSPECTIVES)
        requested = [p for p in requested if p in ALL_PERSPECTIVES]
        if not requested:
            requested = list(DEFAULT_PERSPECTIVES)

        state = ScanState(
            scan_id=scan_id,
            status="scanning",
            repo_url=repo_url,
            branch=branch,
            created_at=now,
            requested_perspectives=requested,
        )
        self._scans[scan_id] = state

        repo_path: Path | None = None
        try:
            # Clone
            repo_path = self._repo_service.clone_repo(repo_url, branch)

            # Scan files and analyze
            files = self._repo_service.scan_files(repo_path)
            all_entities: list[CodeEntity] = []
            all_relationships: list[Relationship] = []
            for file_path, content in files:
                entities, rels = default_registry.analyze_file(file_path, content)
                all_entities.extend(entities)
                all_relationships.extend(rels)

            # Post-process: resolve cross-file relationship targets
            name_to_id: dict[str, str] = {}
            for e in all_entities:
                if e.entity_type in ("class", "model"):
                    name_to_id[e.name] = e.id

            entity_ids = {e.id for e in all_entities}
            resolved_rels: list[Relationship] = []
            for r in all_relationships:
                if r.target_id not in entity_ids:
                    target_name = r.target_id.rsplit("::", 1)[-1] if "::" in r.target_id else ""
                    if target_name in name_to_id:
                        r = Relationship(
                            source_id=r.source_id,
                            target_id=name_to_id[target_name],
                            relationship_type=r.relationship_type,
                            metadata=r.metadata,
                        )
                        resolved_rels.append(r)
                else:
                    resolved_rels.append(r)
            all_relationships = resolved_rels

            # Detect components and inject metadata
            state.components = detect_components(all_entities)

            state.entities = all_entities
            state.relationships = all_relationships

            # Store in knowledge graph if available
            from app.graph import graph_service

            if graph_service.is_available:
                graph_service.store_entities(scan_id, all_entities)
                graph_service.store_relationships(all_relationships)

            # Run perspective analyzers in pipeline order
            for perspective in requested:
                if perspective not in _PERSPECTIVE_ANALYZERS:
                    continue

                # Try graph-powered perspective first, fallback to in-memory
                diagram_data = None
                if graph_service.is_available:
                    diagram_data = graph_service.query_perspective(
                        scan_id, perspective
                    )

                if diagram_data is None:
                    analyzer = _PERSPECTIVE_ANALYZERS[perspective]
                    diagram_data = analyzer.analyze(all_entities, all_relationships)

                state.diagram_data[perspective] = diagram_data

                generator = _MERMAID_GENERATORS[perspective]
                state.mermaid_code[perspective] = generator.generate(diagram_data)

            state.status = "completed"
        except Exception as exc:
            state.status = "failed"
            state.mermaid_code["error"] = str(exc)
        finally:
            if repo_path is not None:
                self._repo_service.cleanup(repo_path)

        return ScanResponse(
            scan_id=state.scan_id,
            status=state.status,
            repo_url=state.repo_url,
            branch=state.branch,
            created_at=state.created_at,
            perspectives=state.requested_perspectives,
            components=list(state.components.keys()),
        )

    def get_scan(self, scan_id: str) -> ScanState | None:
        return self._scans.get(scan_id)

    def get_diagram(self, scan_id: str, perspective: str) -> DiagramResponse | None:
        state = self._scans.get(scan_id)
        if state is None:
            return None
        mermaid = state.mermaid_code.get(perspective)
        if mermaid is None:
            return None
        metadata = {}
        dd = state.diagram_data.get(perspective)
        if dd:
            metadata = dd.metadata
        return DiagramResponse(
            scan_id=scan_id,
            perspective=perspective,
            mermaid_code=mermaid,
            metadata=metadata,
        )

    def list_scans(self) -> list[ScanResponse]:
        return [
            ScanResponse(
                scan_id=s.scan_id,
                status=s.status,
                repo_url=s.repo_url,
                branch=s.branch,
                created_at=s.created_at,
                perspectives=s.requested_perspectives,
                components=list(s.components.keys()),
            )
            for s in self._scans.values()
        ]


orchestrator = ScanOrchestrator()
