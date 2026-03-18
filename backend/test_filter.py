import asyncio
from app.services.scan_orchestrator import orchestrator

def test_filtering():
    resp = orchestrator.start_scan("https://github.com/Joseph-k-iype/ce", "main", ["dataflow", "er"])
    print("Scan status:", resp.status)
    print("Detected components:", resp.components)
    
    state = orchestrator.get_scan(resp.scan_id)
    dd_er = state.diagram_data["er"]
    
    comp = resp.components[0] if resp.components else "None"
    print(f"Testing filter for component: {comp}")
    
    entities = dd_er.entities
    print(f"Total ER entities: {len(entities)}")
    
    filtered = [e for e in entities if e.metadata.get("component") == comp]
    print(f"Filtered ER entities for {comp}: {len(filtered)}")
    
    if len(filtered) == 0 and len(entities) > 0:
        print("First entity metadata:", entities[0].metadata)

if __name__ == "__main__":
    test_filtering()
