import asyncio
from app.services.scan_orchestrator import ScanOrchestrator

def run_test():
    orc = ScanOrchestrator()
    try:
        resp = orc.start_scan("https://github.com/Joseph-k-iype/ce", "main", perspectives=["ingestion", "er", "transformation", "output", "dataflow", "cicd"])
        print("Status:", resp.status)
        state = orc.get_scan(resp.scan_id)
        if "error" in state.mermaid_code:
            print("Error was caught in orchestrator:", state.mermaid_code["error"])
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
