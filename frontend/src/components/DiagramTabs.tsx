import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import FlowGraph from "./FlowGraph";
import MermaidRenderer from "./MermaidRenderer";

const PERSPECTIVES = ["ingestion", "er", "transformation", "output"] as const;

const LABELS: Record<string, string> = {
  ingestion: "Ingestion",
  er: "ER Diagram",
  transformation: "Transformation",
  output: "Output",
};

const PERSPECTIVE_DIRECTIONS: Record<string, "RIGHT" | "DOWN"> = {
  ingestion: "DOWN",
  er: "RIGHT",
  transformation: "RIGHT",
  output: "DOWN",
};

type ViewMode = "graph" | "mermaid";

export default function DiagramTabs({ scanId }: { scanId: string }) {
  const [active, setActive] = useState<string>("ingestion");
  const [viewMode, setViewMode] = useState<ViewMode>("graph");

  // Fetch graph data for React Flow view
  const { data: graphData, isLoading: graphLoading } = useQuery({
    queryKey: ["diagram-data", scanId, active],
    queryFn: () => api.getDiagramData(scanId, active),
    enabled: viewMode === "graph",
  });

  // Fetch Mermaid code (lazy — only when mermaid view is active)
  const { data: mermaidData, isLoading: mermaidLoading } = useQuery({
    queryKey: ["diagram", scanId, active],
    queryFn: () => api.getDiagram(scanId, active),
    enabled: viewMode === "mermaid",
  });

  const copyCode = () => {
    if (mermaidData?.mermaid_code) {
      navigator.clipboard.writeText(mermaidData.mermaid_code);
    }
  };

  return (
    <div>
      {/* Perspective tabs + view toggle */}
      <div className="flex items-center justify-between border-b border-stone-200 mb-4">
        <div className="flex">
          {PERSPECTIVES.map((p) => (
            <button
              key={p}
              onClick={() => setActive(p)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                active === p
                  ? "border-stone-900 text-stone-900"
                  : "border-transparent text-stone-400 hover:text-stone-700"
              }`}
            >
              {LABELS[p]}
            </button>
          ))}
        </div>

        {/* View mode toggle */}
        <div className="flex items-center gap-1 pb-1">
          <button
            onClick={() => setViewMode("graph")}
            className={`text-xs px-2.5 py-1 rounded-md ${
              viewMode === "graph"
                ? "bg-stone-900 text-white"
                : "bg-stone-100 text-stone-500 hover:text-stone-700"
            }`}
          >
            Graph
          </button>
          <button
            onClick={() => setViewMode("mermaid")}
            className={`text-xs px-2.5 py-1 rounded-md ${
              viewMode === "mermaid"
                ? "bg-stone-900 text-white"
                : "bg-stone-100 text-stone-500 hover:text-stone-700"
            }`}
          >
            Mermaid
          </button>
        </div>
      </div>

      {/* React Flow view */}
      {viewMode === "graph" && (
        <FlowGraph
          nodes={graphData?.nodes || []}
          edges={graphData?.edges || []}
          isLoading={graphLoading}
          height="550px"
          maxNodes={150}
          direction={PERSPECTIVE_DIRECTIONS[active] || "RIGHT"}
          showDirectionToggle={true}
          showMiniMap={true}
          emptyMessage={`No entities found for the ${LABELS[active]} perspective.`}
        />
      )}

      {/* Mermaid view */}
      {viewMode === "mermaid" && (
        <div>
          {mermaidLoading && (
            <p className="text-stone-400 text-sm">Loading diagram...</p>
          )}

          {mermaidData && (
            <div>
              <div className="flex justify-end mb-2">
                <button
                  onClick={copyCode}
                  className="text-sm text-stone-500 hover:text-stone-700 px-2 py-1 border border-stone-300 rounded-lg"
                >
                  Copy Mermaid Code
                </button>
              </div>
              <MermaidRenderer code={mermaidData.mermaid_code} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
