from fastapi.testclient import TestClient
from app.main import app
from app.services.scan_orchestrator import orchestrator

def test():
    client = TestClient(app)
    resp = orchestrator.start_scan("https://github.com/Joseph-k-iype/ce", "main", ["dataflow", "er"])
    
    r = client.get(f"/api/scan/{resp.scan_id}/diagrams/er/data", params={"component": "models"})
    print("ER Status:", r.status_code)
    try:
        data = r.json()
        print("ER nodes:", len(data.get("nodes", [])))
    except: pass
        
    r = client.get(f"/api/scan/{resp.scan_id}/diagrams/dataflow/data", params={"component": "models"})
    print("DF Status:", r.status_code)
    try:
        data = r.json()
        print("DF nodes:", len(data.get("nodes", [])))
    except: pass

if __name__ == "__main__":
    test()
