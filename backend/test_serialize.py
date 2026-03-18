from fastapi.testclient import TestClient
from app.main import app
from app.services.scan_orchestrator import orchestrator

def test():
    client = TestClient(app)
    resp = orchestrator.start_scan("https://github.com/Joseph-k-iype/ce", "main", ["dataflow", "er"])
    
    r = client.get(f"/api/scan/{resp.scan_id}/diagrams/er/data")
    data = r.json()
    
    models = [n for n in data["nodes"] if n["properties"].get("component") == "models"]
    print(f"ER models serialized: {len(models)}")
    
    # Let's see ONE of the nodes:
    print(models[0] if models else "None")

if __name__ == "__main__":
    test()
