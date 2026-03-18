from app.services.scan_orchestrator import orchestrator

def test():
    scans = orchestrator.list_scans()
    print("Total scans in memory:", len(scans))
    for s in scans:
        print("  -", s.scan_id)

if __name__ == "__main__":
    test()
