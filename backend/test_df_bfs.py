import asyncio
from app.services.scan_orchestrator import orchestrator
from app.analyzers.dataflow_analyzer import DataFlowAnalyzer

def test():
    resp = orchestrator.start_scan("https://github.com/Joseph-k-iype/ce", "main", ["dataflow"])
    state = orchestrator.get_scan(resp.scan_id)
    
    _DATAFLOW_REL_TYPES = {"calls", "passes_data", "reads", "writes", "produces", "consumes", "uses", "imports"}
    relevant_rels = [r for r in state.relationships if r.relationship_type in _DATAFLOW_REL_TYPES]
    
    forward_adj = {}
    reverse_adj = {}
    for r in relevant_rels:
        forward_adj.setdefault(r.source_id, []).append(r.target_id)
        reverse_adj.setdefault(r.target_id, []).append(r.source_id)
        
    entry_ids = {e.id for e in state.entities if e.entity_type in {"endpoint", "consumer", "file_reader"}}
    exit_ids = {e.id for e in state.entities if e.entity_type in {"db_write", "file_writer", "producer"}}
    
    def _bfs(seeds, adj):
        visited = set()
        queue = list(seeds)
        while queue:
            cur = queue.pop(0)
            if cur in visited: continue
            visited.add(cur)
            for n in adj.get(cur, []):
                if n not in visited: queue.append(n)
        return visited
        
    fwd = _bfs(entry_ids, forward_adj)
    bwd = _bfs(exit_ids, reverse_adj)
    on_path = fwd & bwd
    
    print(f"Entry nodes: {len(entry_ids)}")
    print(f"Exit nodes: {len(exit_ids)}")
    print(f"Forward reachable: {len(fwd)}")
    print(f"Backward reachable: {len(bwd)}")
    print(f"Intersection: {len(on_path)}")

if __name__ == "__main__":
    test()
