import ast
from typing import Any

from app.analyzers.base import CodeAnalyzer
from app.models.domain import CodeEntity, Relationship
from app.utils.determinism import generate_entity_id


# ---------------------------------------------------------------------------
# Decorator / call-name helpers
# ---------------------------------------------------------------------------

def _attr_chain(node: ast.expr) -> str | None:
    """Return dotted name for an Attribute / Name node, e.g. 'app.get'."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _decorator_name(dec: ast.expr) -> str | None:
    if isinstance(dec, ast.Call):
        return _attr_chain(dec.func)
    return _attr_chain(dec)


# ---------------------------------------------------------------------------
# Pattern sets
# ---------------------------------------------------------------------------

_HTTP_ROUTE_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}

_DB_CALL_NAMES = {"query", "filter", "filter_by", "commit", "execute", "add", "delete",
                  "flush", "merge", "refresh", "rollback", "all", "first", "one",
                  "scalar", "count"}
_DB_WRITE_NAMES = {"commit", "execute", "add", "delete", "flush", "merge"}
_DB_READ_NAMES = {"query", "filter", "filter_by", "all", "first", "one", "scalar", "count"}

_FILE_OPEN = {"open"}

_HTTP_CLIENT_NAMES = {"requests.get", "requests.post", "requests.put", "requests.delete",
                      "requests.patch", "requests.head", "requests.options",
                      "httpx.get", "httpx.post", "httpx.put", "httpx.delete",
                      "httpx.patch", "httpx.head", "httpx.options",
                      "httpx.AsyncClient", "requests.Session"}

_PRODUCER_NAMES = {"produce", "publish", "send_message", "send"}
_CONSUMER_NAMES = {"consume", "subscribe", "on_message"}

_BUILTIN_TYPE_NAMES = frozenset({
    "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "None", "Any", "Optional", "bytes", "object", "type", "complex",
})


def _extract_type_names(annotation: ast.expr | None) -> list[str]:
    """Extract referenced type names from a type annotation AST node."""
    if annotation is None:
        return []
    if isinstance(annotation, ast.Name):
        return [annotation.id]
    if isinstance(annotation, ast.Attribute):
        name = _attr_chain(annotation)
        return [name] if name else []
    if isinstance(annotation, ast.Subscript):
        # e.g. list[User], Optional[Order] — recurse into slice
        results = _extract_type_names(annotation.value)
        results.extend(_extract_type_names(annotation.slice))
        return results
    if isinstance(annotation, ast.Tuple):
        # e.g. tuple[str, int]
        out: list[str] = []
        for elt in annotation.elts:
            out.extend(_extract_type_names(elt))
        return out
    if isinstance(annotation, ast.BinOp):
        # e.g. X | Y (union syntax)
        return _extract_type_names(annotation.left) + _extract_type_names(annotation.right)
    if isinstance(annotation, ast.Constant):
        # e.g. string literal forward refs
        if isinstance(annotation.value, str):
            return [annotation.value]
    return []


class PythonASTAnalyzer(CodeAnalyzer):
    """Analyzes Python source files using the ``ast`` module."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".py"]

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    def analyze_file(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            return [], []

        entities: list[CodeEntity] = []
        relationships: list[Relationship] = []

        self._walk_module(tree, file_path, entities, relationships)
        return entities, relationships

    # ------------------------------------------------------------------
    # AST walking
    # ------------------------------------------------------------------

    def _walk_module(
        self,
        tree: ast.Module,
        file_path: str,
        entities: list[CodeEntity],
        relationships: list[Relationship],
    ) -> None:
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                self._handle_class(node, file_path, entities, relationships)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._handle_function(node, file_path, entities, relationships)

    # ------------------------------------------------------------------
    # Classes
    # ------------------------------------------------------------------

    def _handle_class(
        self,
        node: ast.ClassDef,
        file_path: str,
        entities: list[CodeEntity],
        relationships: list[Relationship],
    ) -> None:
        class_id = generate_entity_id(file_path, node.name)

        # --- Extract class attributes ---
        attributes: list[str] = []
        referenced_types: set[str] = set()

        for stmt in node.body:
            # Class-level annotated attributes: x: Type
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                name_str = stmt.target.id
                # Try to get a readable type name
                type_names = _extract_type_names(stmt.annotation)
                type_label = type_names[0] if type_names else "Any"
                attributes.append(f"{name_str}: {type_label}")
                for tn in type_names:
                    if tn not in _BUILTIN_TYPE_NAMES:
                        referenced_types.add(tn)

        # Walk __init__ for self.x = ... assignments and self.x: Type annotations
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name == "__init__":
                for init_stmt in ast.walk(stmt):
                    if isinstance(init_stmt, ast.AnnAssign):
                        if (isinstance(init_stmt.target, ast.Attribute)
                                and isinstance(init_stmt.target.value, ast.Name)
                                and init_stmt.target.value.id == "self"):
                            attr_name = init_stmt.target.attr
                            type_names = _extract_type_names(init_stmt.annotation)
                            type_label = type_names[0] if type_names else "Any"
                            attr_str = f"{attr_name}: {type_label}"
                            if attr_str not in attributes:
                                attributes.append(attr_str)
                            for tn in type_names:
                                if tn not in _BUILTIN_TYPE_NAMES:
                                    referenced_types.add(tn)
                    elif isinstance(init_stmt, ast.Assign):
                        for target in init_stmt.targets:
                            if (isinstance(target, ast.Attribute)
                                    and isinstance(target.value, ast.Name)
                                    and target.value.id == "self"):
                                attr_name = target.attr
                                attr_str = f"{attr_name}: Any"
                                if not any(a.startswith(f"{attr_name}:") for a in attributes):
                                    attributes.append(attr_str)

        # --- Extract method names (excluding dunder methods) ---
        _DUNDER_SKIP = {"__init__", "__str__", "__repr__", "__hash__", "__eq__",
                        "__ne__", "__lt__", "__le__", "__gt__", "__ge__",
                        "__len__", "__bool__", "__del__", "__new__"}
        methods: list[str] = []
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.name not in _DUNDER_SKIP:
                    methods.append(child.name)
                # Collect type refs from method params and return annotations
                for arg in child.args.args:
                    for tn in _extract_type_names(arg.annotation):
                        if tn not in _BUILTIN_TYPE_NAMES:
                            referenced_types.add(tn)
                for tn in _extract_type_names(child.returns):
                    if tn not in _BUILTIN_TYPE_NAMES:
                        referenced_types.add(tn)

        entities.append(
            CodeEntity(
                id=class_id,
                name=node.name,
                entity_type="class",
                file_path=file_path,
                line_number=node.lineno,
                metadata={
                    "decorators": [_decorator_name(d) for d in node.decorator_list if _decorator_name(d)],
                    "attributes": attributes,
                    "methods": methods,
                },
            )
        )

        # Inheritance relationships
        for base in node.bases:
            base_name = _attr_chain(base)
            if base_name:
                base_id = generate_entity_id(file_path, base_name)
                relationships.append(
                    Relationship(
                        source_id=class_id,
                        target_id=base_id,
                        relationship_type="inherits",
                    )
                )

        # "uses" relationships from type annotations
        for type_name in sorted(referenced_types):
            target_id = generate_entity_id(file_path, type_name)
            relationships.append(
                Relationship(
                    source_id=class_id,
                    target_id=target_id,
                    relationship_type="uses",
                )
            )

        # Methods inside the class
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._handle_method(child, node.name, class_id, file_path, entities, relationships)

    # ------------------------------------------------------------------
    # Functions (module-level)
    # ------------------------------------------------------------------

    def _handle_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: str,
        entities: list[CodeEntity],
        relationships: list[Relationship],
    ) -> None:
        # Check for route decorators  ->  endpoint entity
        endpoint = self._extract_endpoint(node)
        func_id = generate_entity_id(file_path, node.name)

        if endpoint:
            eid = generate_entity_id(file_path, f"endpoint::{endpoint['method']}::{endpoint['path']}")
            entities.append(
                CodeEntity(
                    id=eid,
                    name=f"{endpoint['method'].upper()} {endpoint['path']}",
                    entity_type="endpoint",
                    file_path=file_path,
                    line_number=node.lineno,
                    metadata={"http_method": endpoint["method"], "route": endpoint["path"]},
                )
            )
            # Link endpoint → handler function so data flow traces from entry
            relationships.append(
                Relationship(
                    source_id=eid,
                    target_id=func_id,
                    relationship_type="calls",
                )
            )
        entities.append(
            CodeEntity(
                id=func_id,
                name=node.name,
                entity_type="function",
                file_path=file_path,
                line_number=node.lineno,
                metadata={"decorators": [_decorator_name(d) for d in node.decorator_list if _decorator_name(d)]},
            )
        )

        # Walk function body for calls / IO patterns
        self._walk_body(node, func_id, file_path, entities, relationships)

    # ------------------------------------------------------------------
    # Methods (inside a class)
    # ------------------------------------------------------------------

    def _handle_method(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        class_name: str,
        class_id: str,
        file_path: str,
        entities: list[CodeEntity],
        relationships: list[Relationship],
    ) -> None:
        method_name = f"{class_name}.{node.name}"
        method_id = generate_entity_id(file_path, method_name)

        # Check for route decorators  ->  endpoint entity
        endpoint = self._extract_endpoint(node)
        if endpoint:
            eid = generate_entity_id(file_path, f"endpoint::{endpoint['method']}::{endpoint['path']}")
            entities.append(
                CodeEntity(
                    id=eid,
                    name=f"{endpoint['method'].upper()} {endpoint['path']}",
                    entity_type="endpoint",
                    file_path=file_path,
                    line_number=node.lineno,
                    metadata={"http_method": endpoint["method"], "route": endpoint["path"]},
                )
            )
            # Link endpoint → handler method so data flow traces from entry
            relationships.append(
                Relationship(
                    source_id=eid,
                    target_id=method_id,
                    relationship_type="calls",
                )
            )

        entities.append(
            CodeEntity(
                id=method_id,
                name=method_name,
                entity_type="method",
                file_path=file_path,
                line_number=node.lineno,
                metadata={"decorators": [_decorator_name(d) for d in node.decorator_list if _decorator_name(d)]},
            )
        )
        relationships.append(
            Relationship(
                source_id=class_id,
                target_id=method_id,
                relationship_type="contains",
            )
        )

        # Walk method body for calls / IO patterns
        self._walk_body(node, method_id, file_path, entities, relationships)

    # ------------------------------------------------------------------
    # Body walking  (calls, db, file, http, messaging)
    # ------------------------------------------------------------------

    def _walk_body(
        self,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent_id: str,
        file_path: str,
        entities: list[CodeEntity],
        relationships: list[Relationship],
    ) -> None:
        # Collect parameter names for passes_data detection
        param_names: set[str] = set()
        for arg in func_node.args.args:
            if arg.arg != "self":
                param_names.add(arg.arg)

        for node in ast.walk(func_node):
            if not isinstance(node, ast.Call):
                continue

            callee = _attr_chain(node.func) if isinstance(node.func, (ast.Attribute, ast.Name)) else None
            if callee is None:
                continue

            # --- DB operations ---------------------------------------------------
            parts = callee.split(".")
            tail = parts[-1]

            if tail in _DB_WRITE_NAMES:
                eid = generate_entity_id(file_path, f"db_write::{callee}::{getattr(node, 'lineno', 0)}")
                entities.append(
                    CodeEntity(id=eid, name=callee, entity_type="db_write",
                               file_path=file_path, line_number=getattr(node, "lineno", 0))
                )
                relationships.append(
                    Relationship(source_id=parent_id, target_id=eid, relationship_type="writes")
                )
                continue

            if tail in _DB_READ_NAMES:
                eid = generate_entity_id(file_path, f"db_read::{callee}::{getattr(node, 'lineno', 0)}")
                entities.append(
                    CodeEntity(id=eid, name=callee, entity_type="db_read",
                               file_path=file_path, line_number=getattr(node, "lineno", 0))
                )
                relationships.append(
                    Relationship(source_id=parent_id, target_id=eid, relationship_type="reads")
                )
                continue

            # --- File operations -------------------------------------------------
            if tail in _FILE_OPEN or callee in _FILE_OPEN:
                # Determine read vs write from mode argument if possible
                mode = self._infer_file_mode(node)
                if "w" in mode or "a" in mode or "x" in mode:
                    etype = "file_writer"
                    rel = "writes"
                else:
                    etype = "file_reader"
                    rel = "reads"
                eid = generate_entity_id(file_path, f"{etype}::{node.lineno}")
                entities.append(
                    CodeEntity(id=eid, name=f"open()", entity_type=etype,
                               file_path=file_path, line_number=node.lineno)
                )
                relationships.append(
                    Relationship(source_id=parent_id, target_id=eid, relationship_type=rel)
                )
                continue

            if tail in ("read", "readlines", "readline") and len(parts) >= 2:
                eid = generate_entity_id(file_path, f"file_reader::{node.lineno}")
                entities.append(
                    CodeEntity(id=eid, name=callee, entity_type="file_reader",
                               file_path=file_path, line_number=node.lineno)
                )
                relationships.append(
                    Relationship(source_id=parent_id, target_id=eid, relationship_type="reads")
                )
                continue

            if tail == "write" and len(parts) >= 2 and parts[-2] not in ("sys", "stderr", "stdout"):
                eid = generate_entity_id(file_path, f"file_writer::{node.lineno}")
                entities.append(
                    CodeEntity(id=eid, name=callee, entity_type="file_writer",
                               file_path=file_path, line_number=node.lineno)
                )
                relationships.append(
                    Relationship(source_id=parent_id, target_id=eid, relationship_type="writes")
                )
                continue

            # --- HTTP client calls -----------------------------------------------
            if callee in _HTTP_CLIENT_NAMES:
                target_id = generate_entity_id(file_path, f"call::{callee}::{node.lineno}")
                entities.append(
                    CodeEntity(id=target_id, name=callee, entity_type="function",
                               file_path=file_path, line_number=node.lineno,
                               metadata={"kind": "http_client"})
                )
                relationships.append(
                    Relationship(source_id=parent_id, target_id=target_id, relationship_type="calls")
                )
                continue

            # --- Messaging: producers --------------------------------------------
            if tail in _PRODUCER_NAMES:
                eid = generate_entity_id(file_path, f"producer::{callee}::{node.lineno}")
                entities.append(
                    CodeEntity(id=eid, name=callee, entity_type="producer",
                               file_path=file_path, line_number=node.lineno)
                )
                relationships.append(
                    Relationship(source_id=parent_id, target_id=eid, relationship_type="produces")
                )
                continue

            # --- Messaging: consumers --------------------------------------------
            if tail in _CONSUMER_NAMES:
                eid = generate_entity_id(file_path, f"consumer::{callee}::{node.lineno}")
                entities.append(
                    CodeEntity(id=eid, name=callee, entity_type="consumer",
                               file_path=file_path, line_number=node.lineno)
                )
                relationships.append(
                    Relationship(source_id=parent_id, target_id=eid, relationship_type="consumes")
                )
                continue

            # --- Generic function / method calls ---------------------------------
            target_id = generate_entity_id(file_path, callee)
            relationships.append(
                Relationship(source_id=parent_id, target_id=target_id, relationship_type="calls")
            )

            # --- passes_data: parameter forwarding detection ---------------------
            if param_names:
                for arg in node.args:
                    arg_name = None
                    if isinstance(arg, ast.Name):
                        arg_name = arg.id
                    if arg_name and arg_name in param_names:
                        relationships.append(
                            Relationship(
                                source_id=parent_id,
                                target_id=target_id,
                                relationship_type="passes_data",
                                metadata={"param": arg_name},
                            )
                        )
                        break  # one passes_data per call is enough

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_endpoint(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, str] | None:
        """Return {'method': ..., 'path': ...} if the function has a route decorator."""
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call):
                name = _attr_chain(dec.func)
            else:
                name = _attr_chain(dec)
                dec = None  # type: ignore[assignment]

            if name is None:
                continue

            parts = name.split(".")
            method = parts[-1].lower()
            if method in _HTTP_ROUTE_METHODS:
                path = ""
                if dec is not None and isinstance(dec, ast.Call) and dec.args:
                    first_arg = dec.args[0]
                    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                        path = first_arg.value
                return {"method": method, "path": path}
        return None

    @staticmethod
    def _infer_file_mode(call_node: ast.Call) -> str:
        """Try to extract the mode string from an open() call."""
        # open(path, mode) or open(path, mode=mode)
        if len(call_node.args) >= 2:
            arg = call_node.args[1]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
        for kw in call_node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value
        return "r"
