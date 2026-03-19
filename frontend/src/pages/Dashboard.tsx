import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import gsap from "gsap";
import { api } from "../api/client";
import ScanForm from "../components/ScanForm";

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: scans, refetch } = useQuery({
    queryKey: ["scans"],
    queryFn: api.listScans,
  });

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      gsap.fromTo(
        containerRef.current.children,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.5, stagger: 0.1, ease: "power2.out" }
      );
    }
  }, [scans]);

  const handleScanComplete = (scanId: string) => {
    refetch();
    navigate(`/scan/${scanId}`);
  };

  return (
    <div ref={containerRef} className="max-w-2xl mx-auto space-y-8">
      <div className="bg-white border border-stone-200/60 rounded-2xl p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-stone-900 tracking-tight mb-4">Scan a Repository</h2>
        <ScanForm onScanComplete={handleScanComplete} />
      </div>

      {scans && scans.length > 0 && (
        <div className="bg-white border border-stone-200/60 rounded-2xl p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-stone-900 tracking-tight mb-4">Previous Scans</h2>
          <ul className="divide-y divide-stone-100">
            {scans.map((scan) => (
              <li
                key={scan.scan_id}
                className="py-3 flex justify-between items-center cursor-pointer hover:bg-stone-50 px-3 rounded-xl transition-all duration-200"
                onClick={() => navigate(`/scan/${scan.scan_id}`)}
              >
                <div>
                  <p className="text-sm font-medium text-stone-900 truncate max-w-md">
                    {scan.repo_url}
                  </p>
                  <p className="text-xs text-stone-400">
                    {scan.branch} &middot; {scan.status}
                  </p>
                </div>
                <span className="text-xs text-stone-400">
                  {new Date(scan.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
