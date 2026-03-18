import urllib.request
try:
    with urllib.request.urlopen("http://localhost:8000/api/health") as res:
        print(res.read().decode('utf-8'))
except Exception as e:
    print(e)
