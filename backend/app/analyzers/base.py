from abc import ABC, abstractmethod

from app.models.domain import CodeEntity, DiagramData, Relationship


class CodeAnalyzer(ABC):
    """Abstract base class for language-specific code analyzers."""

    @abstractmethod
    def analyze_file(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        """Parse a source file and extract entities and relationships."""
        ...

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """File extensions this analyzer can handle (e.g. ['.py'])."""
        ...


class PerspectiveAnalyzer(ABC):
    """Abstract base class for diagram-perspective analyzers."""

    @abstractmethod
    def analyze(
        self, entities: list[CodeEntity], relationships: list[Relationship]
    ) -> DiagramData:
        """Produce diagram data from a set of entities and relationships."""
        ...

    @property
    @abstractmethod
    def perspective_name(self) -> str:
        """Human-readable name of the perspective (e.g. 'Class Diagram')."""
        ...
