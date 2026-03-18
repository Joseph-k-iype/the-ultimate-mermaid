from fastapi.testclient import TestClient
from app.main import app
import time

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
        
        while True:
            r = client.get(f"/api/scan/{scan_id}")
            if r.json()["status"] == "completed": break
            time.sleep(0.5)
            
        # Now get the diagram data
        r2 = client.get(f"/api/scan/{scan_id}/diagrams/er/data?component=models")
        er_data = r2.json()
        
        print(f"ER nodes returned for 'models': {len(er_data['nodes'])}")
        for e in er_data["nodes"][:2]:
            print(e)
            
        r3 = client.get(f"/api/scan/{scan_id}/diagrams/er?component=models")
        er_mermaid = r3.json()
        print("Mermaid contains namespace models:", "namespace models" in er_mermaid["mermaid_code"])
            
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test()
