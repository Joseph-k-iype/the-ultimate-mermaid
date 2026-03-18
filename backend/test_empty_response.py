import requests

def test():
    import urllib.request
    import json
    
    req = urllib.request.Request("http://localhost:8000/scan", data=json.dumps({
        "repo_url": "https://github.com/Joseph-k-iype/ce",
        "branch": "main",
        "perspectives": ["er", "dataflow"]
    }).encode(), headers={"Content-Type": "application/json"})
    
    resp = urllib.request.urlopen(req)
    scan_id = json.loads(resp.read())["scan_id"]
    
    url = f"http://localhost:8000/scan/{scan_id}/diagrams/er/data?component=models"
    r = requests.get(url)
    data = r.json()
    
    print("ER nodes:", len(data.get("nodes", [])))
    print("ER edges:", len(data.get("edges", [])))
    
    url = f"http://localhost:8000/scan/{scan_id}/diagrams/dataflow/data?component=models"
    r = requests.get(url)
    data = r.json()
    
    print("DF nodes:", len(data.get("nodes", [])))
    print("DF edges:", len(data.get("edges", [])))

if __name__ == "__main__":
    test()
