from fastapi.testclient import TestClient
from app.main import app

def test():
    client = TestClient(app)
    # Trigger an actual scan through the API just like the frontend
    r = client.post("/api/scan", json={
        "repo_url": "https://github.com/Joseph-k-iype/ce",
        "branch": "main",
        "perspectives": ["er", "dataflow"]
    })
    
    print("Scan Response Status:", r.status_code)
    try:
        data = r.json()
        scan_id = data["scan_id"]
        
        # Now get the diagram data
        r2 = client.get(f"/api/scan/{scan_id}/diagrams/er/data")
        er_data = r2.json()
        
        models = [n for n in er_data["nodes"] if n["properties"].get("component") == "models"]
        print(f"ER models serialized: {len(models)}")
        
        # Let's see ONE of the nodes:
        if er_data["nodes"]:
            print(er_data["nodes"][0])
            
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test()
