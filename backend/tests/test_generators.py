from app.analyzers.er_analyzer import ERAnalyzer
from app.analyzers.ingestion_analyzer import IngestionAnalyzer
from app.analyzers.output_analyzer import OutputAnalyzer
from app.analyzers.transformation_analyzer import TransformationAnalyzer
from app.generators.er_generator import ERMermaidGenerator
from app.generators.ingestion_generator import IngestionMermaidGenerator
from app.generators.output_generator import OutputMermaidGenerator
from app.generators.transformation_generator import TransformationMermaidGenerator


class TestERGenerator:
    def test_generates_er_diagram(self, sample_entities, sample_relationships):
        analyzer = ERAnalyzer()
        data = analyzer.analyze(sample_entities, sample_relationships)
        gen = ERMermaidGenerator()
        code = gen.generate(data)
        assert code.startswith("erDiagram")

    def test_determinism(self, sample_entities, sample_relationships):
        analyzer = ERAnalyzer()
        gen = ERMermaidGenerator()
        results = set()
        for _ in range(5):
            data = analyzer.analyze(sample_entities, sample_relationships)
            results.add(gen.generate(data))
        assert len(results) == 1


class TestIngestionGenerator:
    def test_generates_flowchart(self, sample_entities, sample_relationships):
        analyzer = IngestionAnalyzer()
        data = analyzer.analyze(sample_entities, sample_relationships)
        gen = IngestionMermaidGenerator()
        code = gen.generate(data)
        assert code.startswith("flowchart TD")

    def test_determinism(self, sample_entities, sample_relationships):
        analyzer = IngestionAnalyzer()
        gen = IngestionMermaidGenerator()
        results = set()
        for _ in range(5):
            data = analyzer.analyze(sample_entities, sample_relationships)
            results.add(gen.generate(data))
        assert len(results) == 1


class TestTransformationGenerator:
    def test_generates_flowchart_lr(self, sample_entities, sample_relationships):
        analyzer = TransformationAnalyzer()
        data = analyzer.analyze(sample_entities, sample_relationships)
        gen = TransformationMermaidGenerator()
        code = gen.generate(data)
        assert code.startswith("flowchart LR")

    def test_determinism(self, sample_entities, sample_relationships):
        analyzer = TransformationAnalyzer()
        gen = TransformationMermaidGenerator()
        results = set()
        for _ in range(5):
            data = analyzer.analyze(sample_entities, sample_relationships)
            results.add(gen.generate(data))
        assert len(results) == 1


class TestOutputGenerator:
    def test_generates_flowchart(self, sample_entities, sample_relationships):
        analyzer = OutputAnalyzer()
        data = analyzer.analyze(sample_entities, sample_relationships)
        gen = OutputMermaidGenerator()
        code = gen.generate(data)
        assert code.startswith("flowchart TD")

    def test_determinism(self, sample_entities, sample_relationships):
        analyzer = OutputAnalyzer()
        gen = OutputMermaidGenerator()
        results = set()
        for _ in range(5):
            data = analyzer.analyze(sample_entities, sample_relationships)
            results.add(gen.generate(data))
        assert len(results) == 1
