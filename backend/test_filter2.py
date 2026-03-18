import asyncio
from app.services.scan_orchestrator import orchestrator

def test_filtering():
    resp = orchestrator.start_scan("https://github.com/Joseph-k-iype/ce", "main", ["dataflow", "er"])
    
    state = orchestrator.get_scan(resp.scan_id)
    comp = "models"
    
    print(f"Testing filter for component: '{comp}' on scan: {resp.scan_id}")
    
    dd = state.diagram_data.get("er")
    if not dd:
        print("No ER data")
        return
        
    entities = dd.entities
    relationships = dd.relationships
    
    core_ids = {e.id for e in entities if e.metadata.get("component") == comp}
    print(f"Core ER entities found: {len(core_ids)}")
    
    filtered_rels = [
        r for r in relationships
        if r.source_id in core_ids or r.target_id in core_ids
    ]
    print(f"1-hop ER rels found: {len(filtered_rels)}")
    
    required_ids = core_ids.copy()
    for r in filtered_rels:
        required_ids.add(r.source_id)
        required_ids.add(r.target_id)
        
    print(f"Total ER required entities: {len(required_ids)}")
    
    # Try DataFlow
    dd_df = state.diagram_data.get("dataflow")
    if dd_df:
        entities_df = dd_df.entities
        core_ids_df = {e.id for e in entities_df if e.metadata.get("component") == comp}
        print(f"Core DataFlow entities found: {len(core_ids_df)}")
        
if __name__ == "__main__":
    test_filtering()
