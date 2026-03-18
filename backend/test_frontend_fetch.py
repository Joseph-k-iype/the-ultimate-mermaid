import asyncio
from app.services.scan_orchestrator import orchestrator
from app.routes.scan import get_diagram_data

def test():
    # Attempt simulated get_diagram_data call
    resp = orchestrator.start_scan("https://github.com/Joseph-k-iype/ce", "main", ["dataflow", "er"])
    
    # Try the er component filter
    try:
        from fastapi import Request
        # Just manually call the inner logic of get_diagram_data
        state = orchestrator.get_scan(resp.scan_id)
        if not state: return
        dd = state.diagram_data.get("er")
        
        comp = "models"
        entities = dd.entities
        core = {e.id for e in entities if e.metadata.get("component") == comp}
        filtered_rels = [r for r in dd.relationships if r.source_id in core or r.target_id in core]
        required = core.copy()
        for r in filtered_rels:
            required.add(r.source_id)
            required.add(r.target_id)
            
        final_nodes = [e for e in entities if e.id in required]
        print(f"ER Nodes returned for '{comp}': {len(final_nodes)}")
        
        # Dataflow
        dd_df = state.diagram_data.get("dataflow")
        comp = "models"
        entities_df = dd_df.entities
        core_df = {e.id for e in entities_df if e.metadata.get("component") == comp}
        filtered_rels_df = [r for r in dd_df.relationships if r.source_id in core_df or r.target_id in core_df]
        required_df = core_df.copy()
        for r in filtered_rels_df:
            required_df.add(r.source_id)
            required_df.add(r.target_id)
            
        final_nodes_df = [e for e in entities_df if e.id in required_df]
        print(f"DataFlow Nodes returned for '{comp}': {len(final_nodes_df)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
