import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import MermaidRenderer from "./MermaidRenderer";

const PERSPECTIVES = ["ingestion", "er", "transformation", "output"] as const;

const LABELS: Record<string, string> = {
  ingestion: "Ingestion",
  er: "ER Diagram",
  transformation: "Transformation",
  output: "Output",
};

export default function DiagramTabs({ scanId }: { scanId: string }) {
  const [active, setActive] = useState<string>("ingestion");

  const { data, isLoading, error } = useQuery({
    queryKey: ["diagram", scanId, active],
    queryFn: () => api.getDiagram(scanId, active),
  });

  const copyCode = () => {
    if (data?.mermaid_code) {
      navigator.clipboard.writeText(data.mermaid_code);
    }
  };

  return (
    <div>
      <div className="flex border-b border-stone-200 mb-4">
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

      {isLoading && <p className="text-stone-400 text-sm">Loading diagram...</p>}
      {error && <p className="text-red-500 text-sm">Error: {(error as Error).message}</p>}

      {data && (
        <div>
          <div className="flex justify-end mb-2">
            <button
              onClick={copyCode}
              className="text-sm text-stone-500 hover:text-stone-700 px-2 py-1 border border-stone-300 rounded-lg"
            >
              Copy Mermaid Code
            </button>
          </div>
          <MermaidRenderer code={data.mermaid_code} />
        </div>
      )}
    </div>
  );
}
