from fastapi.testclient import TestClient
from app.main import app

def test():
    client = TestClient(app)
    r = client.delete("/api/scan")
    print("Deleted all scans:", r.status_code)

if __name__ == "__main__":
    test()
