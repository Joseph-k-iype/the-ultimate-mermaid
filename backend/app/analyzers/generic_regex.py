import os
import re
from typing import Any

from app.analyzers.base import CodeAnalyzer
from app.models.domain import CodeEntity, Relationship
from app.utils.determinism import generate_entity_id


# ======================================================================
# Compiled pattern sets keyed by language group
# ======================================================================

# --- JavaScript / TypeScript ------------------------------------------

_JS_CLASS = re.compile(
    r"^(?:export\s+)?(?:default\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?",
    re.MULTILINE,
)
_JS_FUNCTION = re.compile(
    r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)",
    re.MULTILINE,
)
_JS_ARROW = re.compile(
    r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(",
    re.MULTILINE,
)
_JS_EXPORT_DEFAULT = re.compile(
    r"^export\s+default\s+(\w+)",
    re.MULTILINE,
)
_JS_IMPORT = re.compile(
    r"^import\s+(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)?\s*(?:,\s*(?:\{[^}]*\}|\w+))?\s*from\s+['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)
_JS_EXPRESS_ROUTE = re.compile(
    r"(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)

# --- Java -------------------------------------------------------------

_JAVA_CLASS = re.compile(
    r"^(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?",
    re.MULTILINE,
)
_JAVA_INTERFACE = re.compile(
    r"^(?:public\s+)?interface\s+(\w+)",
    re.MULTILINE,
)
_JAVA_METHOD = re.compile(
    r"^\s+(?:public|private|protected)\s+(?:static\s+)?(?:[\w<>\[\],\s]+?)\s+(\w+)\s*\(",
    re.MULTILINE,
)
_JAVA_MAPPING = re.compile(
    r"@(RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)"
    r'(?:\s*\(\s*(?:value\s*=\s*)?["\']([^"\']*)["\'])?\s*\)',
    re.MULTILINE,
)

# --- Go ---------------------------------------------------------------

_GO_FUNC = re.compile(
    r"^func\s+(?:\(\s*\w+\s+\*?\w+\s*\)\s+)?(\w+)\s*\(",
    re.MULTILINE,
)
_GO_STRUCT = re.compile(
    r"^type\s+(\w+)\s+struct\s*\{",
    re.MULTILINE,
)
_GO_TYPE = re.compile(
    r"^type\s+(\w+)\s+(?!struct\b)(\w+)",
    re.MULTILINE,
)
_GO_HANDLE = re.compile(
    r'http\.HandleFunc\s*\(\s*["\']([^"\']+)["\']',
    re.MULTILINE,
)

# Mapping from method-annotation prefix to HTTP method
_JAVA_MAPPING_METHODS: dict[str, str] = {
    "RequestMapping": "request",
    "GetMapping": "get",
    "PostMapping": "post",
    "PutMapping": "put",
    "DeleteMapping": "delete",
    "PatchMapping": "patch",
}


# ======================================================================
# Helper: which language family does an extension belong to?
# ======================================================================

def _language_group(ext: str) -> str:
    if ext in {".js", ".jsx", ".ts", ".tsx"}:
        return "js"
    if ext == ".java":
        return "java"
    if ext == ".go":
        return "go"
    return "unknown"


class GenericRegexAnalyzer(CodeAnalyzer):
    """Regex-based analyzer for JS/TS, Java, and Go source files."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".js", ".ts", ".tsx", ".jsx", ".java", ".go"]

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def analyze_file(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        ext = os.path.splitext(file_path)[1].lower()
        lang = _language_group(ext)
        dispatch = {
            "js": self._analyze_js,
            "java": self._analyze_java,
            "go": self._analyze_go,
        }
        handler = dispatch.get(lang)
        if handler is None:
            return [], []
        return handler(file_path, content)

    # ------------------------------------------------------------------
    # JS / TS
    # ------------------------------------------------------------------

    def _analyze_js(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        entities: list[CodeEntity] = []
        relationships: list[Relationship] = []
        lines = content.splitlines()

        # Classes
        for m in _JS_CLASS.finditer(content):
            cls_name = m.group(1)
            base_name = m.group(2)
            line = content[: m.start()].count("\n") + 1
            cls_id = generate_entity_id(file_path, cls_name)
            entities.append(
                CodeEntity(id=cls_id, name=cls_name, entity_type="class",
                           file_path=file_path, line_number=line)
            )
            if base_name:
                base_id = generate_entity_id(file_path, base_name)
                relationships.append(
                    Relationship(source_id=cls_id, target_id=base_id, relationship_type="inherits")
                )

        # Regular functions
        for m in _JS_FUNCTION.finditer(content):
            name = m.group(1)
            line = content[: m.start()].count("\n") + 1
            entities.append(
                CodeEntity(id=generate_entity_id(file_path, name), name=name,
                           entity_type="function", file_path=file_path, line_number=line)
            )

        # Arrow functions assigned to const/let
        for m in _JS_ARROW.finditer(content):
            name = m.group(1)
            line = content[: m.start()].count("\n") + 1
            entities.append(
                CodeEntity(id=generate_entity_id(file_path, name), name=name,
                           entity_type="function", file_path=file_path, line_number=line,
                           metadata={"arrow": True})
            )

        # export default <Identifier>
        for m in _JS_EXPORT_DEFAULT.finditer(content):
            name = m.group(1)
            line = content[: m.start()].count("\n") + 1
            eid = generate_entity_id(file_path, f"export_default::{name}")
            target_id = generate_entity_id(file_path, name)
            entities.append(
                CodeEntity(id=eid, name=f"export default {name}",
                           entity_type="variable", file_path=file_path, line_number=line)
            )
            relationships.append(
                Relationship(source_id=eid, target_id=target_id, relationship_type="uses")
            )

        # import statements
        for m in _JS_IMPORT.finditer(content):
            module = m.group(1)
            line = content[: m.start()].count("\n") + 1
            imp_id = generate_entity_id(file_path, f"import::{module}")
            entities.append(
                CodeEntity(id=imp_id, name=module, entity_type="variable",
                           file_path=file_path, line_number=line,
                           metadata={"kind": "import"})
            )
            relationships.append(
                Relationship(source_id=generate_entity_id(file_path, file_path),
                             target_id=imp_id, relationship_type="imports")
            )

        # Express-style routes
        for m in _JS_EXPRESS_ROUTE.finditer(content):
            method = m.group(1)
            path = m.group(2)
            line = content[: m.start()].count("\n") + 1
            eid = generate_entity_id(file_path, f"endpoint::{method}::{path}")
            entities.append(
                CodeEntity(id=eid, name=f"{method.upper()} {path}",
                           entity_type="endpoint", file_path=file_path, line_number=line,
                           metadata={"http_method": method, "route": path})
            )

        return entities, relationships

    # ------------------------------------------------------------------
    # Java
    # ------------------------------------------------------------------

    def _analyze_java(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        entities: list[CodeEntity] = []
        relationships: list[Relationship] = []

        current_class_id: str | None = None

        # Classes
        for m in _JAVA_CLASS.finditer(content):
            cls_name = m.group(1)
            base_name = m.group(2)
            line = content[: m.start()].count("\n") + 1
            cls_id = generate_entity_id(file_path, cls_name)
            current_class_id = cls_id
            entities.append(
                CodeEntity(id=cls_id, name=cls_name, entity_type="class",
                           file_path=file_path, line_number=line)
            )
            if base_name:
                base_id = generate_entity_id(file_path, base_name)
                relationships.append(
                    Relationship(source_id=cls_id, target_id=base_id, relationship_type="inherits")
                )

        # Interfaces
        for m in _JAVA_INTERFACE.finditer(content):
            name = m.group(1)
            line = content[: m.start()].count("\n") + 1
            iid = generate_entity_id(file_path, name)
            entities.append(
                CodeEntity(id=iid, name=name, entity_type="class",
                           file_path=file_path, line_number=line,
                           metadata={"kind": "interface"})
            )

        # Methods
        for m in _JAVA_METHOD.finditer(content):
            name = m.group(1)
            line = content[: m.start()].count("\n") + 1
            mid = generate_entity_id(file_path, name)
            entities.append(
                CodeEntity(id=mid, name=name, entity_type="method",
                           file_path=file_path, line_number=line)
            )
            if current_class_id:
                relationships.append(
                    Relationship(source_id=current_class_id, target_id=mid,
                                 relationship_type="contains")
                )

        # Spring mapping annotations
        for m in _JAVA_MAPPING.finditer(content):
            annotation = m.group(1)
            path = m.group(2) or ""
            method = _JAVA_MAPPING_METHODS.get(annotation, "request")
            line = content[: m.start()].count("\n") + 1
            eid = generate_entity_id(file_path, f"endpoint::{method}::{path}")
            entities.append(
                CodeEntity(id=eid, name=f"{method.upper()} {path}",
                           entity_type="endpoint", file_path=file_path, line_number=line,
                           metadata={"http_method": method, "route": path})
            )

        return entities, relationships

    # ------------------------------------------------------------------
    # Go
    # ------------------------------------------------------------------

    def _analyze_go(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        entities: list[CodeEntity] = []
        relationships: list[Relationship] = []

        # Structs
        for m in _GO_STRUCT.finditer(content):
            name = m.group(1)
            line = content[: m.start()].count("\n") + 1
            entities.append(
                CodeEntity(id=generate_entity_id(file_path, name), name=name,
                           entity_type="class", file_path=file_path, line_number=line,
                           metadata={"kind": "struct"})
            )

        # Type definitions (non-struct)
        for m in _GO_TYPE.finditer(content):
            name = m.group(1)
            underlying = m.group(2)
            line = content[: m.start()].count("\n") + 1
            entities.append(
                CodeEntity(id=generate_entity_id(file_path, name), name=name,
                           entity_type="variable", file_path=file_path, line_number=line,
                           metadata={"kind": "type_alias", "underlying": underlying})
            )

        # Functions (including methods with receivers)
        for m in _GO_FUNC.finditer(content):
            name = m.group(1)
            line = content[: m.start()].count("\n") + 1
            entities.append(
                CodeEntity(id=generate_entity_id(file_path, name), name=name,
                           entity_type="function", file_path=file_path, line_number=line)
            )

        # http.HandleFunc patterns -> endpoints
        for m in _GO_HANDLE.finditer(content):
            path = m.group(1)
            line = content[: m.start()].count("\n") + 1
            eid = generate_entity_id(file_path, f"endpoint::handle::{path}")
            entities.append(
                CodeEntity(id=eid, name=f"HANDLE {path}",
                           entity_type="endpoint", file_path=file_path, line_number=line,
                           metadata={"http_method": "handle", "route": path})
            )

        return entities, relationships
