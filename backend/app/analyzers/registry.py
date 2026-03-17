import os
from typing import Any

from app.analyzers.base import CodeAnalyzer
from app.models.domain import CodeEntity, Relationship


class AnalyzerRegistry:
    """Singleton registry that maps file extensions to CodeAnalyzer instances."""

    _instance: "AnalyzerRegistry | None" = None

    def __new__(cls) -> "AnalyzerRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._analyzers = {}
        return cls._instance

    def __init__(self) -> None:
        # _analyzers is set in __new__ to survive repeated __init__ calls.
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, analyzer: CodeAnalyzer) -> None:
        """Register an analyzer for each of its supported extensions."""
        for ext in analyzer.supported_extensions:
            self._analyzers[ext.lower()] = analyzer

    def get_analyzer(self, file_path: str) -> CodeAnalyzer | None:
        """Return the analyzer for the given file's extension, or None."""
        ext = os.path.splitext(file_path)[1].lower()
        return self._analyzers.get(ext)

    def analyze_file(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        """Convenience method: look up the right analyzer and run it."""
        analyzer = self.get_analyzer(file_path)
        if analyzer is None:
            return [], []
        return analyzer.analyze_file(file_path, content)

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (useful for testing)."""
        cls._instance = None


def _build_default_registry() -> AnalyzerRegistry:
    """Create and populate a registry with the built-in analyzers."""
    from app.analyzers.python_ast import PythonASTAnalyzer
    from app.analyzers.generic_regex import GenericRegexAnalyzer

    registry = AnalyzerRegistry()
    registry.register(PythonASTAnalyzer())
    registry.register(GenericRegexAnalyzer())
    return registry


default_registry: AnalyzerRegistry = _build_default_registry()
