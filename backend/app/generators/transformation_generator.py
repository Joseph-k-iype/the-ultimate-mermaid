from app.generators.base import MermaidGenerator
from app.models.domain import DiagramData, FlowNode


class TransformationMermaidGenerator(MermaidGenerator):
    """Generates Mermaid flowchart LR diagrams for data transformation pipelines."""

    @property
    def diagram_type(self) -> str:
        return "transformation"

    def generate(self, data: DiagramData) -> str:
        lines: list[str] = ["flowchart LR"]

        if not data.flow_nodes:
            lines.append("    %% No data available")
            lines.append('    empty["No transformation data"]')
            return "\n".join(lines)

        flow_nodes = data.flow_nodes

        # Truncate if too many nodes
        if len(flow_nodes) > 80:
            lines.append(f"    %% Showing top 80 of {len(flow_nodes)} nodes")
            # Keep nodes that have the most connections
            conn_counts: dict[str, int] = {}
            for node in flow_nodes:
                conn_counts[node.id] = len(node.connections)
                for conn in node.connections:
                    conn_counts[conn] = conn_counts.get(conn, 0) + 1
            flow_nodes = sorted(
                flow_nodes,
                key=lambda n: (-conn_counts.get(n.id, 0), n.id),
            )[:80]
            kept_ids = {n.id for n in flow_nodes}
            for node in flow_nodes:
                node.connections = [c for c in node.connections if c in kept_ids]

        sorted_nodes = sorted(flow_nodes, key=lambda n: n.id)

        # Emit node definitions
        for node in sorted_nodes:
            lines.append(self._render_node(node))

        # Emit edges
        for node in sorted_nodes:
            sid = self.sanitize_id(node.id)
            for conn in sorted(node.connections):
                tid = self.sanitize_id(conn)
                lines.append(f"    {sid} --> {tid}")

        return "\n".join(lines)

    def _render_node(self, node: FlowNode) -> str:
        sid = self.sanitize_id(node.id)
        label = self.sanitize_label(node.label)

        if node.node_type == "input":
            return f'    {sid}[/"{label}"/]'
        elif node.node_type == "output":
            return f'    {sid}[\\"{label}"\\]'
        else:
            # transform or any other type
            return f'    {sid}["{label}"]'
