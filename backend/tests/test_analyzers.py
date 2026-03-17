from app.analyzers.python_ast import PythonASTAnalyzer
from app.analyzers.generic_regex import GenericRegexAnalyzer


class TestPythonASTAnalyzer:
    def setup_method(self):
        self.analyzer = PythonASTAnalyzer()

    def test_supported_extensions(self):
        assert ".py" in self.analyzer.supported_extensions

    def test_detects_class(self):
        code = "class MyModel:\n    name: str\n    def save(self): pass\n"
        entities, rels = self.analyzer.analyze_file("models.py", code)
        class_entities = [e for e in entities if e.entity_type == "class"]
        assert len(class_entities) >= 1
        assert class_entities[0].name == "MyModel"
        assert class_entities[0].id == "models.py::MyModel"

    def test_detects_function(self):
        code = "def helper(x):\n    return x + 1\n"
        entities, _ = self.analyzer.analyze_file("utils.py", code)
        funcs = [e for e in entities if e.entity_type == "function"]
        assert any(f.name == "helper" for f in funcs)

    def test_detects_endpoint_decorator(self):
        code = '@app.get("/users")\ndef list_users():\n    pass\n'
        entities, _ = self.analyzer.analyze_file("routes.py", code)
        endpoints = [e for e in entities if e.entity_type == "endpoint"]
        assert len(endpoints) >= 1

    def test_entity_id_format(self):
        code = "class Foo:\n    pass\n"
        entities, _ = self.analyzer.analyze_file("src/foo.py", code)
        for e in entities:
            assert "::" in e.id
            assert e.id.startswith("src/foo.py::")


class TestGenericRegexAnalyzer:
    def setup_method(self):
        self.analyzer = GenericRegexAnalyzer()

    def test_supported_extensions(self):
        exts = self.analyzer.supported_extensions
        assert ".js" in exts
        assert ".ts" in exts
        assert ".java" in exts
        assert ".go" in exts

    def test_detects_js_class(self):
        code = "class UserService {\n  constructor() {}\n}\n"
        entities, _ = self.analyzer.analyze_file("service.js", code)
        classes = [e for e in entities if e.entity_type == "class"]
        assert any(c.name == "UserService" for c in classes)

    def test_detects_js_function(self):
        code = "function fetchData() {\n  return fetch('/api');\n}\n"
        entities, _ = self.analyzer.analyze_file("api.js", code)
        funcs = [e for e in entities if e.entity_type == "function"]
        assert any(f.name == "fetchData" for f in funcs)

    def test_detects_ts_arrow_function(self):
        code = "const process = (data: string) => {\n  return data;\n};\n"
        entities, _ = self.analyzer.analyze_file("util.ts", code)
        funcs = [e for e in entities if e.entity_type == "function"]
        assert any(f.name == "process" for f in funcs)

    def test_entity_id_format(self):
        code = "class Foo {}\n"
        entities, _ = self.analyzer.analyze_file("src/bar.js", code)
        for e in entities:
            assert "::" in e.id
            assert e.id.startswith("src/bar.js::")
