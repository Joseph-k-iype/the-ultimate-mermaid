from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.analyzers.er_analyzer import ERAnalyzer
from app.analyzers.ingestion_analyzer import IngestionAnalyzer
from app.analyzers.output_analyzer import OutputAnalyzer
from app.analyzers.registry import default_registry
from app.analyzers.transformation_analyzer import TransformationAnalyzer
from app.generators.er_generator import ERMermaidGenerator
from app.generators.ingestion_generator import IngestionMermaidGenerator
from app.generators.output_generator import OutputMermaidGenerator
from app.generators.transformation_generator import TransformationMermaidGenerator
from app.models.domain import CodeEntity, DiagramData, Relationship
from app.models.responses import DiagramResponse, ScanResponse
from app.services.repo_service import RepoService
from app.utils.determinism import generate_scan_id

PERSPECTIVES = ("ingestion", "er", "transformation", "output")

_PERSPECTIVE_ANALYZERS = {
    "ingestion": IngestionAnalyzer(),
    "er": ERAnalyzer(),
    "transformation": TransformationAnalyzer(),
    "output": OutputAnalyzer(),
}

_MERMAID_GENERATORS = {
    "ingestion": IngestionMermaidGenerator(),
    "er": ERMermaidGenerator(),
    "transformation": TransformationMermaidGenerator(),
    "output": OutputMermaidGenerator(),
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


class ScanOrchestrator:
    """Orchestrates the full scan pipeline: clone → analyze → generate diagrams."""

    def __init__(self) -> None:
        self._scans: dict[str, ScanState] = {}
        self._repo_service = RepoService()

    def start_scan(self, repo_url: str, branch: str) -> ScanResponse:
        scan_id = generate_scan_id(repo_url, branch)
        now = datetime.now(timezone.utc)

        state = ScanState(
            scan_id=scan_id,
            status="scanning",
            repo_url=repo_url,
            branch=branch,
            created_at=now,
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

            state.entities = all_entities
            state.relationships = all_relationships

            # Store in knowledge graph if available
            from app.graph import graph_service

            if graph_service.is_available:
                graph_service.store_entities(scan_id, all_entities)
                graph_service.store_relationships(all_relationships)

            # Run perspective analyzers and generators
            for perspective in PERSPECTIVES:
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
            )
            for s in self._scans.values()
        ]


orchestrator = ScanOrchestrator()
