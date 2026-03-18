import asyncio
from app.services.scan_orchestrator import orchestrator

def test():
    resp = orchestrator.start_scan("https://github.com/Joseph-k-iype/ce", "main", ["dataflow", "er"])
    state = orchestrator.get_scan(resp.scan_id)
    
    entities = state.entities
    models = [e for e in entities if e.file_path.startswith("models/")]
    
    for m in models[:5]:
        print(f"Model ID: {m.id}, Name: {m.name}, File: {m.file_path}, Component: {m.metadata.get('component')}")

if __name__ == "__main__":
    test()
