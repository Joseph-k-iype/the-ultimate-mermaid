import requests

def test():
    import urllib.request
    import json
    
    # Let's query the local uvicorn server directly with an OPTIONS request
    req = urllib.request.Request("http://localhost:8000/api/scan/566e59bc228f662ad64524eb971e1a88bc894bb9f41e4d9463b5a7a217007167/diagrams/er/data?component=models", method="OPTIONS")
    req.add_header("Origin", "http://localhost:5173")
    req.add_header("Access-Control-Request-Method", "GET")
    
    try:
        resp = urllib.request.urlopen(req)
        print("OPTIONS Status:", resp.status)
        print("Headers:", dict(resp.headers))
    except Exception as e:
        print("Error:", dict(getattr(e, 'headers', {})))

if __name__ == "__main__":
    test()
