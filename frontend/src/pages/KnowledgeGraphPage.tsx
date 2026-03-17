import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import FlowGraph from "../components/FlowGraph";

export default function KnowledgeGraphPage() {
  const [scanId, setScanId] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  const { data: status } = useQuery({
    queryKey: ["graph-status"],
    queryFn: api.getGraphStatus,
  });

  const { data: graphData, isLoading } = useQuery({
    queryKey: ["knowledge-graph", scanId],
    queryFn: () => api.getKnowledgeGraph(scanId || undefined),
  });

  const { data: scans } = useQuery({
    queryKey: ["scans"],
    queryFn: api.listScans,
  });

  // Apply search filter before passing to FlowGraph
  const filteredNodes = useMemo(() => {
    if (!graphData) return [];
    if (!searchTerm) return graphData.nodes;
    const q = searchTerm.toLowerCase();
    return graphData.nodes.filter(
      (n) => n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q)
    );
  }, [graphData, searchTerm]);

  const filteredEdges = useMemo(() => {
    if (!graphData) return [];
    const ids = new Set(filteredNodes.map((n) => n.id));
    return graphData.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
  }, [graphData, filteredNodes]);

  // Empty state
  if (
    !isLoading &&
    (!graphData || graphData.nodes.length === 0) &&
    (!status || !status.available)
  ) {
    return (
      <div className="max-w-3xl mx-auto">
        <h1 className="text-xl font-semibold text-stone-900 tracking-tight mb-6">
          Knowledge Graph
        </h1>
        <div className="bg-white border border-stone-200 rounded-xl p-8 text-center">
          <div className="text-3xl mb-3 text-stone-300">{"\u2B21"}</div>
          <p className="text-stone-600 text-sm mb-2">
            No graph data yet. Scan a repository to visualize its code entities
            and relationships.
          </p>
          <p className="text-stone-400 text-xs">
            For persistent graph storage, run{" "}
            <code className="bg-stone-100 px-1 rounded">
              docker run -p 6379:6379 falkordb/falkordb
            </code>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 100px)" }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <h1 className="text-xl font-semibold text-stone-900 tracking-tight">
          Knowledge Graph
        </h1>
        <div className="flex items-center gap-3 text-xs text-stone-400">
          {status && (
            <span className={status.available ? "text-emerald-600" : "text-stone-400"}>
              {status.available ? "FalkorDB connected" : "In-memory mode"}
            </span>
          )}
        </div>
      </div>

      {/* Controls */}
      <div className="bg-white border border-stone-200 rounded-xl p-3 mb-3 flex-shrink-0">
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="border border-stone-300 rounded-lg px-3 py-1.5 text-sm w-48 focus:ring-2 focus:ring-stone-400 focus:outline-none"
          />
          <select
            value={scanId}
            onChange={(e) => setScanId(e.target.value)}
            className="border border-stone-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-stone-400 focus:outline-none"
          >
            <option value="">All scans</option>
            {scans?.map((s) => (
              <option key={s.scan_id} value={s.scan_id}>
                {s.repo_url.split("/").pop()} ({s.branch})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Graph */}
      <div className="flex-1 min-h-0">
        <FlowGraph
          nodes={filteredNodes}
          edges={filteredEdges}
          isLoading={isLoading}
          height="100%"
          maxNodes={300}
          direction="RIGHT"
          showDirectionToggle={true}
          showMiniMap={true}
          emptyMessage="No graph data available. Scan a repository to populate the knowledge graph."
        />
      </div>
    </div>
  );
}
