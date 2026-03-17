import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import DiagramTabs from "../components/DiagramTabs";

export default function DiagramPage() {
  const { scanId } = useParams<{ scanId: string }>();

  const { data: scan, isLoading } = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => api.getScan(scanId!),
    enabled: !!scanId,
  });

  if (!scanId) return <p className="text-red-500">Missing scan ID</p>;
  if (isLoading) return <p className="text-stone-400 text-sm">Loading...</p>;

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {scan && (
        <div className="bg-white border border-stone-200 rounded-xl p-4">
          <p className="text-sm text-stone-600 truncate">
            <span className="font-medium text-stone-900">Repo:</span> {scan.repo_url}
          </p>
          <p className="text-sm text-stone-600">
            <span className="font-medium text-stone-900">Branch:</span> {scan.branch} &middot;{" "}
            <span
              className={
                scan.status === "completed" ? "text-emerald-600" : "text-amber-600"
              }
            >
              {scan.status}
            </span>
          </p>
        </div>
      )}
      <div className="bg-white border border-stone-200 rounded-xl p-6">
        <DiagramTabs scanId={scanId} />
      </div>
    </div>
  );
}
