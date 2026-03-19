import { useState, useMemo, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import gsap from "gsap";
import { api } from "../api/client";
import FlowGraph from "../components/FlowGraph";

export default function KnowledgeGraphPage() {
  const pageRef = useRef<HTMLDivElement>(null);
  const [scanId, setScanId] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  const { data: status } = useQuery({
    queryKey: ["graph-status"],
    queryFn: api.getGraphStatus,
  });

  const { data: scans } = useQuery({
    queryKey: ["scans"],
    queryFn: api.listScans,
  });

  // Auto-select the most recent scan
  useEffect(() => {
    if (!scanId && scans && scans.length > 0) {
      setScanId(scans[0].scan_id);
    }
  }, [scans, scanId]);

  useEffect(() => {
    if (pageRef.current) {
      gsap.fromTo(
        pageRef.current.children,
        { opacity: 0, y: 12 },
        { opacity: 1, y: 0, duration: 0.4, stagger: 0.08, ease: "power2.out" }
      );
    }
  }, []);

  // Only fetch when we have a scan selected
  const { data: graphData, isLoading } = useQuery({
    queryKey: ["knowledge-graph", scanId],
    queryFn: () => api.getKnowledgeGraph(scanId),
    enabled: !!scanId,
  });

  // Search filter
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

  // Current scan info
  const currentScan = scans?.find((s) => s.scan_id === scanId);
  const repoName = currentScan
    ? currentScan.repo_url.replace(/\.git$/, "").split("/").slice(-2).join("/")
    : "";

  // Empty state — no scans at all
  if (!scans || scans.length === 0) {
    return (
      <div className="max-w-3xl mx-auto">
        <h1 className="text-xl font-semibold text-stone-900 tracking-tight mb-6">
          Knowledge Graph
        </h1>
        <div className="bg-white border border-stone-200 rounded-xl p-8 text-center">
          <div className="text-3xl mb-3 text-stone-300">{"\u2B21"}</div>
          <p className="text-stone-600 text-sm mb-2">
            No scans yet. Scan a repository from the Dashboard to visualize its
            code entities and relationships.
          </p>
          <p className="text-stone-400 text-xs">
            Each scan produces its own isolated knowledge graph.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div ref={pageRef} className="flex flex-col" style={{ height: "calc(100vh - 80px)" }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <div>
          <h1 className="text-xl font-semibold text-stone-900 tracking-tight">
            Knowledge Graph
          </h1>
          {repoName && (
            <p className="text-xs text-stone-400 mt-0.5">
              {repoName}
              {currentScan && (
                <span className="ml-1 text-stone-300">
                  ({currentScan.branch})
                </span>
              )}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-stone-400">
          {status && (
            <span className={status.available ? "text-emerald-600" : "text-stone-400"}>
              {status.available ? "FalkorDB" : "In-memory"}
            </span>
          )}
        </div>
      </div>

      {/* Controls */}
      <div className="bg-white border border-stone-200/60 rounded-2xl p-3 mb-3 flex-shrink-0 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-xs text-stone-400 whitespace-nowrap">Repository:</label>
            <select
              value={scanId}
              onChange={(e) => {
                setScanId(e.target.value);
                setSearchTerm("");
              }}
              className="border border-stone-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-stone-400 focus:outline-none"
            >
              {scans.map((s) => {
                const name = s.repo_url.replace(/\.git$/, "").split("/").pop();
                return (
                  <option key={s.scan_id} value={s.scan_id}>
                    {name} ({s.branch})
                  </option>
                );
              })}
            </select>
          </div>
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="border border-stone-300 rounded-lg px-3 py-1.5 text-sm w-48 focus:ring-2 focus:ring-stone-400 focus:outline-none"
          />
        </div>
      </div>

      {/* Graph */}
      <div className="flex-1 min-h-0">
        <FlowGraph
          nodes={filteredNodes}
          edges={filteredEdges}
          isLoading={isLoading || !scanId}
          height="100%"
          direction="RIGHT"
          showDirectionToggle={true}
          showMiniMap={true}
          emptyMessage="No entities found for this scan."
        />
      </div>
    </div>
  );
}
