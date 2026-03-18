from fastapi.testclient import TestClient
from app.main import app

def test():
    client = TestClient(app)
    r = client.post("/api/scan", json={"repo_url": "https://github.com/Joseph-k-iype/ce", "branch": "main", "perspectives": ["er"]})
    scan_id = r.json()["scan_id"]
    
    r2 = client.get(f"/api/scan/{scan_id}/diagrams/er?component=models")
    er_data = r2.json()
    
    code = er_data["mermaid_code"]
    print(code)
        
if __name__ == "__main__":
    test()
