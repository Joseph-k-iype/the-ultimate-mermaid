from app.analyzers.python_ast import PythonASTAnalyzer
from app.analyzers.er_analyzer import ERAnalyzer
from app.analyzers.dataflow_analyzer import DataFlowAnalyzer
from app.generators.er_generator import ERMermaidGenerator
from app.generators.dataflow_generator import DataFlowMermaidGenerator
from app.utils.determinism import (
    canonical_sort_entities,
    canonical_sort_relationships,
    generate_entity_id,
    generate_scan_id,
)


class TestDeterministicIds:
    def test_entity_id_stable(self):
        for _ in range(10):
            assert generate_entity_id("a.py", "Foo") == "a.py::Foo"

    def test_scan_id_stable(self):
        ids = {generate_scan_id("https://repo", "main") for _ in range(10)}
        assert len(ids) == 1


class TestCanonicalSorting:
    def test_sort_entities(self, sample_entities):
        sorted1 = canonical_sort_entities(sample_entities)
        sorted2 = canonical_sort_entities(list(reversed(sample_entities)))
        assert [e.id for e in sorted1] == [e.id for e in sorted2]

    def test_sort_relationships(self, sample_relationships):
        sorted1 = canonical_sort_relationships(sample_relationships)
        sorted2 = canonical_sort_relationships(list(reversed(sample_relationships)))
        assert [(r.source_id, r.target_id) for r in sorted1] == [
            (r.source_id, r.target_id) for r in sorted2
        ]


class TestSnapshotDeterminism:
    """Run same analysis twice and assert identical output."""

    SAMPLE_CODE = '''\
class User:
    name: str
    email: str

    def save(self):
        pass

class Order:
    total: float
    user_id: int

@app.get("/users")
def get_users():
    pass

def process(data):
    return data
'''

    def test_python_analysis_determinism(self):
        analyzer = PythonASTAnalyzer()
        r1_entities, r1_rels = analyzer.analyze_file("app.py", self.SAMPLE_CODE)
        r2_entities, r2_rels = analyzer.analyze_file("app.py", self.SAMPLE_CODE)
        assert [e.model_dump() for e in r1_entities] == [
            e.model_dump() for e in r2_entities
        ]
        assert [r.model_dump() for r in r1_rels] == [r.model_dump() for r in r2_rels]

    def test_er_pipeline_determinism(self):
        analyzer = PythonASTAnalyzer()
        er = ERAnalyzer()
        gen = ERMermaidGenerator()

        entities, rels = analyzer.analyze_file("app.py", self.SAMPLE_CODE)
        code1 = gen.generate(er.analyze(entities, rels))
        code2 = gen.generate(er.analyze(entities, rels))
        assert code1 == code2

    def test_dataflow_pipeline_determinism(self):
        analyzer = PythonASTAnalyzer()
        df = DataFlowAnalyzer()
        gen = DataFlowMermaidGenerator()

        entities, rels = analyzer.analyze_file("app.py", self.SAMPLE_CODE)
        code1 = gen.generate(df.analyze(entities, rels))
        code2 = gen.generate(df.analyze(entities, rels))
        assert code1 == code2
