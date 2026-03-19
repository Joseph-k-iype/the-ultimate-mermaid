import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import gsap from "gsap";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import DiagramTabs from "../components/DiagramTabs";
import PublishPatternModal from "../components/PublishPatternModal";
import AgentInsightsPanel from "../components/agents/AgentInsightsPanel";

export default function DiagramPage() {
  const { scanId } = useParams<{ scanId: string }>();

  const { data: scan, isLoading } = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => api.getScan(scanId!),
    enabled: !!scanId,
  });

  const [showPublish, setShowPublish] = useState(false);
  const pageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (pageRef.current) {
      gsap.fromTo(
        pageRef.current.children,
        { opacity: 0, y: 16 },
        { opacity: 1, y: 0, duration: 0.4, stagger: 0.08, ease: "power2.out" }
      );
    }
  }, [scan]);

  if (!scanId) return <p className="text-red-500">Missing scan ID</p>;
  if (isLoading) return <p className="text-stone-400 text-sm">Loading...</p>;

  return (
    <div ref={pageRef} className="flex gap-5 max-w-7xl mx-auto">
      <div className="flex-1 min-w-0 space-y-4">
        {scan && (
          <div className="bg-white border border-stone-200/60 rounded-2xl p-5 relative shadow-sm">
            <div className="absolute top-4 right-4">
              <button
                onClick={() => setShowPublish(true)}
                className="bg-stone-900 text-white px-3 py-1.5 text-sm rounded-lg hover:bg-stone-800"
              >
                Publish Scan as Pattern
              </button>
            </div>
            <p className="text-sm text-stone-600 truncate pr-40">
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
            {scan.components && scan.components.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                <span className="text-xs text-stone-500 mt-0.5">Components:</span>
                {scan.components.map((c) => (
                  <span
                    key={c}
                    className="text-xs px-2 py-0.5 bg-stone-100 text-stone-600 rounded"
                  >
                    {c}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
        <div className="bg-white border border-stone-200/60 rounded-2xl p-6 shadow-sm">
          <DiagramTabs
            scanId={scanId}
            perspectives={scan?.perspectives}
            components={scan?.components}
          />
        </div>

        {/* Publish full scan modal */}
        {showPublish && scan && (
          <PublishPatternModal
            scanId={scanId}
            perspectives={scan.perspectives}
            activePerspective="all" // Signal to pre-select all
            onClose={() => setShowPublish(false)}
            components={scan.components}
          />
        )}
      </div>

      {scan && scan.status === "completed" && (
        <div className="w-80 flex-shrink-0">
          <div className="sticky top-20 bg-white border border-stone-200/60 rounded-2xl overflow-hidden shadow-sm">
            <AgentInsightsPanel scanId={scanId} scanStatus={scan.status} />
          </div>
        </div>
      )}
    </div>
  );
}
