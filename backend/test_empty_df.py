import asyncio
from app.services.scan_orchestrator import orchestrator

def test():
    resp = orchestrator.start_scan("https://github.com/Joseph-k-iype/ce", "main", ["dataflow"])
    state = orchestrator.get_scan(resp.scan_id)
    dd_df = state.diagram_data.get("dataflow")
    
    # Let's see what component names exist in the df entities
    components = {}
    for e in dd_df.entities:
        c = e.metadata.get("component", "MISSING")
        components[c] = components.get(c, 0) + 1
    print("DataFlow Components:", components)
    
if __name__ == "__main__":
    test()
