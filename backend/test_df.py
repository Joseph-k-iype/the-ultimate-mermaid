import asyncio
from app.services.scan_orchestrator import orchestrator

def test_filtering():
    resp = orchestrator.start_scan("https://github.com/Joseph-k-iype/ce", "main", ["dataflow", "er"])
    state = orchestrator.get_scan(resp.scan_id)
    
    dd_df = state.diagram_data.get("dataflow")
    if not dd_df:
        print("No DF data")
        return
        
    print(f"Total DF Entities: {len(dd_df.entities)}")
    
    comp = "models"
    entities_df = dd_df.entities
    core_ids_df = {e.id for e in entities_df if e.metadata.get("component") == comp}
    print(f"Core DataFlow entities for '{comp}': {len(core_ids_df)}")
    
    # Check if ANY models exist in the raw entities BEFORE data flow filtering
    raw_models = {e.id for e in state.entities if e.metadata.get("component") == comp}
    print(f"Raw entities for '{comp}': {len(raw_models)}")

if __name__ == "__main__":
    test_filtering()
