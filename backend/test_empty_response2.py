from fastapi.testclient import TestClient
from app.main import app
from app.services.scan_orchestrator import orchestrator

def test():
    client = TestClient(app)
    
    # We must scan first to populate state. Let's just use the server orchestrator directly
    resp = orchestrator.start_scan("https://github.com/Joseph-k-iype/ce", "main", ["dataflow", "er"])
    scan_id = resp.scan_id
    
    r = client.get(f"/scan/{scan_id}/diagrams/er/data", params={"component": "models"})
    print("ER Status:", r.status_code)
    try:
        data = r.json()
        print("ER nodes returned to frontend:", len(data.get("nodes", [])))
        print("ER edges returned to frontend:", len(data.get("edges", [])))
    except Exception as e:
        print(e)
        
    r = client.get(f"/scan/{scan_id}/diagrams/dataflow/data", params={"component": "models"})
    print("DF Status:", r.status_code)
    try:
        data = r.json()
        print("DF nodes returned to frontend:", len(data.get("nodes", [])))
        print("DF edges returned to frontend:", len(data.get("edges", [])))
        
        # Are there ANY flow_nodes returned? No, get_diagram_data uses dd.entities.
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test()
