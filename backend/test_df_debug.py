import asyncio
from app.services.scan_orchestrator import orchestrator

def test():
    resp = orchestrator.start_scan("https://github.com/Joseph-k-iype/ce", "main", ["dataflow"])
    state = orchestrator.get_scan(resp.scan_id)
    entities = state.entities
    rels = state.relationships
    
    _DATAFLOW_REL_TYPES = {"calls", "passes_data", "reads", "writes", "produces", "consumes", "uses", "imports"}
    relevant_rels = [r for r in rels if r.relationship_type in _DATAFLOW_REL_TYPES]
    
    forward_adj = {}
    reverse_adj = {}
    for r in relevant_rels:
        forward_adj.setdefault(r.source_id, []).append(r.target_id)
        reverse_adj.setdefault(r.target_id, []).append(r.source_id)
        
    entry_ids = {e.id for e in entities if e.entity_type in {"endpoint", "consumer", "file_reader"}}
    exit_ids = {e.id for e in entities if e.entity_type in {"db_write", "file_writer", "producer"}}
    
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
        
    on_path = _bfs(entry_ids, forward_adj) & _bfs(exit_ids, reverse_adj)
    
    # Simulate step 5
    if on_path:
        _DATA_ACCESS_RELS = {"reads", "writes", "produces", "consumes", "passes_data", "uses", "imports"}
        added_new = True
        iterations = 0
        while added_new:
            iterations += 1
            added_new = False
            for r in relevant_rels:
                if r.relationship_type in _DATA_ACCESS_RELS:
                    if r.source_id in on_path and r.target_id not in on_path:
                        print(f"Adding (forward) from {r.source_id} -> {r.target_id} [{r.relationship_type}]")
                        on_path.add(r.target_id)
                        added_new = True
                    elif r.target_id in on_path and r.source_id not in on_path:
                        print(f"Adding (backward) from {r.source_id} -> {r.target_id} [{r.relationship_type}]")
                        on_path.add(r.source_id)
                        added_new = True
        print(f"Finished step 5 in {iterations} iterations.")
        
    filtered = [e for e in entities if e.id in on_path and e.entity_type in {"function", "method", "endpoint", "class", "model", "db_read", "db_write", "file_reader", "file_writer", "consumer", "producer"}]
    comp_counts = {}
    for e in filtered:
        c = e.metadata.get("component")
        comp_counts[c] = comp_counts.get(c, 0) + 1
    print("Components:", comp_counts)

if __name__ == "__main__":
    test()
