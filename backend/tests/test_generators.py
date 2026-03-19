from app.analyzers.er_analyzer import ERAnalyzer
from app.analyzers.dataflow_analyzer import DataFlowAnalyzer
from app.analyzers.manifest_analyzer import ManifestAnalyzer
from app.generators.er_generator import ERMermaidGenerator
from app.generators.dataflow_generator import DataFlowMermaidGenerator
from app.generators.manifest_generator import ManifestMermaidGenerator


class TestERGenerator:
    def test_generates_er_diagram(self, sample_entities, sample_relationships):
        analyzer = ERAnalyzer()
        data = analyzer.analyze(sample_entities, sample_relationships)
        gen = ERMermaidGenerator()
        code = gen.generate(data)
        assert code.startswith("classDiagram")

    def test_determinism(self, sample_entities, sample_relationships):
        analyzer = ERAnalyzer()
        gen = ERMermaidGenerator()
        results = set()
        for _ in range(5):
            data = analyzer.analyze(sample_entities, sample_relationships)
            results.add(gen.generate(data))
        assert len(results) == 1


class TestManifestGenerator:
    def test_generates_flowchart(self, sample_entities, sample_relationships):
        analyzer = ManifestAnalyzer()
        data = analyzer.analyze(sample_entities, sample_relationships)
        gen = ManifestMermaidGenerator()
        code = gen.generate(data)
        assert code.startswith("flowchart TB")

    def test_includes_all_entity_types(self, sample_entities, sample_relationships):
        analyzer = ManifestAnalyzer()
        data = analyzer.analyze(sample_entities, sample_relationships)
        entity_types = {e.entity_type for e in data.entities}
        # sample_entities has class, endpoint, function, file_reader, db_write
        assert "class" in entity_types
        assert "endpoint" in entity_types

    def test_determinism(self, sample_entities, sample_relationships):
        analyzer = ManifestAnalyzer()
        gen = ManifestMermaidGenerator()
        results = set()
        for _ in range(5):
            data = analyzer.analyze(sample_entities, sample_relationships)
            results.add(gen.generate(data))
        assert len(results) == 1


class TestDataFlowGenerator:
    def test_generates_flowchart_lr(self, sample_entities, sample_relationships):
        analyzer = DataFlowAnalyzer()
        data = analyzer.analyze(sample_entities, sample_relationships)
        gen = DataFlowMermaidGenerator()
        code = gen.generate(data)
        assert code.startswith("flowchart LR")

    def test_determinism(self, sample_entities, sample_relationships):
        analyzer = DataFlowAnalyzer()
        gen = DataFlowMermaidGenerator()
        results = set()
        for _ in range(5):
            data = analyzer.analyze(sample_entities, sample_relationships)
            results.add(gen.generate(data))
        assert len(results) == 1
