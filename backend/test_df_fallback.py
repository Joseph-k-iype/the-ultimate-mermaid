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
        
    # intersection
    on_path = _bfs(entry_ids, forward_adj) & _bfs(exit_ids, reverse_adj)
    print("Strict flow path nodes:", len(on_path))
    
    # ── 6. Fallback: if no complete paths, use all participants ─────
    # Right now fallback only happens if on_path is EMPTY.
    # But for a backend with 2000 nodes, having ONE complete path (size 50) means 1950 nodes are dropped. 
    # Data models will vanish. Should we fallback to all participants anyways if intersection is very small compared to total?
    # Or should we just include all models related to participants?
    on_path_all = set()
    for r in relevant_rels:
        on_path_all.add(r.source_id)
        on_path_all.add(r.target_id)
    
    print("All participants:", len(on_path_all))
    
    filtered_all = [e for e in entities if e.id in on_path_all and e.entity_type in {"function", "method", "endpoint", "class", "model", "db_read", "db_write", "file_reader", "file_writer", "consumer", "producer"}]
    c_counts = {}
    for e in filtered_all:
        c = e.metadata.get("component")
        c_counts[c] = c_counts.get(c, 0) + 1
    print("Components for all participants:", c_counts)

if __name__ == "__main__":
    test()
