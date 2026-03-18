import asyncio
from app.services.scan_orchestrator import orchestrator

def test():
    resp = orchestrator.start_scan("https://github.com/Joseph-k-iype/ce", "main", ["dataflow"])
    state = orchestrator.get_scan(resp.scan_id)
    
    _DATAFLOW_REL_TYPES = {"calls", "passes_data", "reads", "writes", "produces", "consumes", "uses", "imports"}
    relevant_rels = [r for r in state.relationships if r.relationship_type in _DATAFLOW_REL_TYPES]
    
    print("Relevant rels count:", len(relevant_rels))
    types = {}
    for r in relevant_rels:
        types[r.relationship_type] = types.get(r.relationship_type, 0) + 1
    print("Relationship types:", types)
    
    # Are there ANY rels touching a model?
    model_ids = {e.id for e in state.entities if e.metadata.get("component") == "models"}
    touching_models = [r for r in relevant_rels if r.source_id in model_ids or r.target_id in model_ids]
    print(f"Rels touching models: {len(touching_models)}")
    if touching_models:
        for r in touching_models[:5]:
            print(f"  {r.relationship_type}: {r.source_id} -> {r.target_id}")

if __name__ == "__main__":
    test()
