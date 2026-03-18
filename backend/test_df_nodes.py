import asyncio
from app.services.scan_orchestrator import orchestrator

def test():
    resp = orchestrator.start_scan("https://github.com/Joseph-k-iype/ce", "main", ["dataflow", "er"])
    state = orchestrator.get_scan(resp.scan_id)
    
    dd = state.diagram_data.get("dataflow")
    for n in dd.entities:
        print(f"Entity: {n.name}, Metadata Component: {n.metadata.get('component')}")

    print("\n--- Flow Nodes ---")
    for fn in dd.flow_nodes:
        print(f"Flow Node: {fn.label}")

if __name__ == "__main__":
    test()
