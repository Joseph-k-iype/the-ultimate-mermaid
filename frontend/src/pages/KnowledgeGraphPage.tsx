import { useState, useCallback, useEffect, useMemo, memo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
  MarkerType,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import ELK from "elkjs/lib/elk.bundled.js";
import {
  api,
  type GraphNode as ApiGraphNode,
  type GraphEdge as ApiGraphEdge,
} from "../api/client";

// ── Palette ──────────────────────────────────────────────────────────
const TYPE_PALETTE: Record<
  string,
  { bg: string; border: string; text: string; icon: string }
> = {
  class: { bg: "#faf5ff", border: "#c084fc", text: "#6b21a8", icon: "C" },
  function: { bg: "#ecfdf5", border: "#6ee7b7", text: "#065f46", icon: "f" },
  method: { bg: "#f0fdf4", border: "#86efac", text: "#166534", icon: "m" },
  variable: { bg: "#fefce8", border: "#fde047", text: "#713f12", icon: "v" },
  endpoint: { bg: "#eff6ff", border: "#60a5fa", text: "#1e40af", icon: "E" },
  model: { bg: "#fdf4ff", border: "#d946ef", text: "#86198f", icon: "M" },
  consumer: { bg: "#fff7ed", border: "#fb923c", text: "#9a3412", icon: ">" },
  producer: { bg: "#fce7f3", border: "#f472b6", text: "#9d174d", icon: "<" },
  file_reader: {
    bg: "#f0fdf4",
    border: "#4ade80",
    text: "#166534",
    icon: "\u2190",
  },
  file_writer: {
    bg: "#fff1f2",
    border: "#fb7185",
    text: "#9f1239",
    icon: "\u2192",
  },
  db_read: { bg: "#eff6ff", border: "#3b82f6", text: "#1e3a5f", icon: "\u25B7" },
  db_write: { bg: "#fef2f2", border: "#ef4444", text: "#991b1b", icon: "\u25C1" },
};
const DEFAULT_PAL = {
  bg: "#f5f5f4",
  border: "#d6d3d1",
  text: "#57534e",
  icon: "?",
};

// ── Custom node ──────────────────────────────────────────────────────
type EntityNodeData = {
  label: string;
  entityType: string;
  filePath: string;
};

const EntityNode = memo(({ data }: NodeProps<Node<EntityNodeData>>) => {
  const pal = TYPE_PALETTE[data.entityType] || DEFAULT_PAL;
  return (
    <div
      style={{
        background: pal.bg,
        border: `1.5px solid ${pal.border}`,
        borderRadius: 10,
        padding: "6px 12px",
        fontSize: 11,
        color: pal.text,
        fontWeight: 500,
        display: "flex",
        alignItems: "center",
        gap: 6,
        maxWidth: 220,
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <span
        style={{
          width: 18,
          height: 18,
          borderRadius: 4,
          background: pal.border + "40",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 10,
          fontWeight: 700,
          flexShrink: 0,
        }}
      >
        {pal.icon}
      </span>
      <span
        style={{ overflow: "hidden", textOverflow: "ellipsis" }}
        title={`${data.label}\n${data.filePath}`}
      >
        {data.label}
      </span>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
});
EntityNode.displayName = "EntityNode";

const nodeTypes = { entity: EntityNode };

// ── ELK layout ───────────────────────────────────────────────────────
const elk = new ELK();

async function elkLayout(
  nodes: Node[],
  edges: Edge[],
  direction: "RIGHT" | "DOWN" = "RIGHT"
): Promise<{ nodes: Node[]; edges: Edge[] }> {
  const groups = new Map<string, string[]>();
  for (const n of nodes) {
    const g = (n.data?.group as string) || "other";
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g)!.push(n.id);
  }

  const elkChildren = [...groups.entries()].map(([group, ids]) => ({
    id: `group_${group}`,
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": direction,
      "elk.spacing.nodeNode": "20",
      "elk.layered.spacing.nodeNodeBetweenLayers": "40",
    },
    children: ids.map((id) => ({
      id,
      width: 200,
      height: 36,
    })),
    edges: edges
      .filter((e) => ids.includes(e.source) && ids.includes(e.target))
      .map((e) => ({
        id: e.id,
        sources: [e.source],
        targets: [e.target],
      })),
  }));

  // Cross-group edges
  const crossEdges = edges
    .filter((e) => {
      const sg = (nodes.find((n) => n.id === e.source)?.data?.group as string) || "other";
      const tg = (nodes.find((n) => n.id === e.target)?.data?.group as string) || "other";
      return sg !== tg;
    })
    .map((e) => ({
      id: `cross_${e.id}`,
      sources: [e.source],
      targets: [e.target],
    }));

  const graph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": direction,
      "elk.spacing.nodeNode": "25",
      "elk.layered.spacing.nodeNodeBetweenLayers": "80",
      "elk.hierarchyHandling": "INCLUDE_CHILDREN",
      "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
      "elk.edgeRouting": "POLYLINE",
    },
    children: elkChildren,
    edges: crossEdges,
  };

  try {
    const result = await elk.layout(graph);

    const posMap = new Map<string, { x: number; y: number }>();
    for (const group of result.children || []) {
      const gx = group.x || 0;
      const gy = group.y || 0;
      for (const child of group.children || []) {
        posMap.set(child.id, { x: gx + (child.x || 0), y: gy + (child.y || 0) });
      }
    }

    return {
      nodes: nodes.map((n) => ({
        ...n,
        position: posMap.get(n.id) || { x: 0, y: 0 },
      })),
      edges,
    };
  } catch {
    // Fallback: simple grid
    let x = 0;
    let y = 0;
    return {
      nodes: nodes.map((n, i) => {
        const pos = { x, y };
        x += 240;
        if ((i + 1) % 10 === 0) {
          x = 0;
          y += 60;
        }
        return { ...n, position: pos };
      }),
      edges,
    };
  }
}

// ── Helpers ──────────────────────────────────────────────────────────
function getGroup(entityType: string): string {
  if (["class", "function", "method", "variable"].includes(entityType))
    return "CodeConstruct";
  if (["endpoint", "model"].includes(entityType)) return "APIElement";
  if (["db_read", "db_write", "file_reader", "file_writer"].includes(entityType))
    return "DataAccessor";
  if (["consumer", "producer"].includes(entityType)) return "MessageHandler";
  return "Other";
}

function buildElements(
  apiNodes: ApiGraphNode[],
  apiEdges: ApiGraphEdge[],
  filterTypes: Set<string>,
  searchTerm: string,
  maxNodes: number
): { nodes: Node[]; edges: Edge[]; total: number; shown: number } {
  let filtered = apiNodes;

  if (filterTypes.size > 0) {
    filtered = filtered.filter((n) => {
      const et = (n.properties?.entity_type as string) || n.type;
      return filterTypes.has(et);
    });
  }
  if (searchTerm) {
    const q = searchTerm.toLowerCase();
    filtered = filtered.filter(
      (n) =>
        n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q)
    );
  }

  const total = filtered.length;
  const display = filtered.slice(0, maxNodes);
  const shown = display.length;
  const idSet = new Set(display.map((n) => n.id));

  const nodes: Node[] = display.map((n) => {
    const et = (n.properties?.entity_type as string) || "class";
    return {
      id: n.id,
      type: "entity",
      data: {
        label: n.label,
        entityType: et,
        filePath: (n.properties?.file_path as string) || "",
        group: getGroup(et),
      },
      position: { x: 0, y: 0 },
    };
  });

  const edges: Edge[] = apiEdges
    .filter((e) => idSet.has(e.source) && idSet.has(e.target))
    .map((e, i) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      label: e.type,
      type: "smoothstep",
      animated: e.type === "CALLS" || e.type === "calls",
      style: { stroke: "#a8a29e", strokeWidth: 1.2 },
      labelStyle: { fontSize: 9, fill: "#78716c" },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: "#a8a29e",
        width: 12,
        height: 12,
      },
    }));

  return { nodes, edges, total, shown };
}

// ── Legend ────────────────────────────────────────────────────────────
function Legend({
  types,
  active,
  onToggle,
}: {
  types: string[];
  active: Set<string>;
  onToggle: (t: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1">
      {types.map((t) => {
        const pal = TYPE_PALETTE[t] || DEFAULT_PAL;
        const isActive = active.size === 0 || active.has(t);
        return (
          <button
            key={t}
            onClick={() => onToggle(t)}
            className="text-[10px] px-1.5 py-0.5 rounded transition-opacity"
            style={{
              background: pal.bg,
              border: `1px solid ${pal.border}`,
              color: pal.text,
              opacity: isActive ? 1 : 0.35,
            }}
          >
            {pal.icon} {t}
          </button>
        );
      })}
    </div>
  );
}

// ── Inner component (needs ReactFlowProvider) ────────────────────────
function KnowledgeGraphInner() {
  const [scanId, setScanId] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [filterTypes, setFilterTypes] = useState<Set<string>>(new Set());
  const [direction, setDirection] = useState<"RIGHT" | "DOWN">("RIGHT");
  const [layoutBusy, setLayoutBusy] = useState(false);
  const maxNodes = 200;

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

  const [rfNodes, setRfNodes, onNodesChange] = useNodesState<Node>([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [info, setInfo] = useState({ total: 0, shown: 0 });

  const toggleType = useCallback((type: string) => {
    setFilterTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }, []);

  const allEntityTypes = useMemo(() => {
    if (!graphData) return [];
    const types = new Set<string>();
    for (const n of graphData.nodes) {
      types.add((n.properties?.entity_type as string) || n.type);
    }
    return [...types].sort();
  }, [graphData]);

  // Build + layout whenever data/filters change
  useEffect(() => {
    if (!graphData || graphData.nodes.length === 0) {
      setRfNodes([]);
      setRfEdges([]);
      setInfo({ total: 0, shown: 0 });
      return;
    }

    const { nodes, edges, total, shown } = buildElements(
      graphData.nodes,
      graphData.edges,
      filterTypes,
      searchTerm,
      maxNodes
    );

    if (nodes.length === 0) {
      setRfNodes([]);
      setRfEdges([]);
      setInfo({ total, shown: 0 });
      return;
    }

    setInfo({ total, shown });
    setLayoutBusy(true);

    elkLayout(nodes, edges, direction).then(({ nodes: ln, edges: le }) => {
      setRfNodes(ln);
      setRfEdges(le);
      setLayoutBusy(false);
    });
  }, [graphData, filterTypes, searchTerm, maxNodes, direction, setRfNodes, setRfEdges]);

  const miniMapColor = useCallback((node: Node) => {
    const et = (node.data?.entityType as string) || "";
    return (TYPE_PALETTE[et] || DEFAULT_PAL).border;
  }, []);

  // ── Empty state ──
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
            No graph data yet. Scan a repository to visualize its code entities and
            relationships.
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
      {/* Header bar */}
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <h1 className="text-xl font-semibold text-stone-900 tracking-tight">
          Knowledge Graph
        </h1>
        <div className="flex items-center gap-3 text-xs text-stone-400">
          {status && (
            <span
              className={
                status.available ? "text-emerald-600" : "text-stone-400"
              }
            >
              {status.available ? "FalkorDB connected" : "In-memory mode"}
            </span>
          )}
          <span>{info.shown} nodes</span>
          {info.total > info.shown && (
            <span className="text-amber-600">
              of {info.total}
            </span>
          )}
        </div>
      </div>

      {/* Controls row */}
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

          <div className="flex items-center gap-1 border-l border-stone-200 pl-3">
            <span className="text-xs text-stone-400 mr-1">Layout:</span>
            <button
              onClick={() => setDirection("RIGHT")}
              className={`text-xs px-2 py-1 rounded-lg ${
                direction === "RIGHT"
                  ? "bg-stone-900 text-white"
                  : "bg-stone-100 text-stone-600"
              }`}
            >
              Horizontal
            </button>
            <button
              onClick={() => setDirection("DOWN")}
              className={`text-xs px-2 py-1 rounded-lg ${
                direction === "DOWN"
                  ? "bg-stone-900 text-white"
                  : "bg-stone-100 text-stone-600"
              }`}
            >
              Vertical
            </button>
          </div>
        </div>
      </div>

      {/* Graph canvas — fills remaining height */}
      <div className="flex-1 bg-white border border-stone-200 rounded-xl overflow-hidden relative min-h-0">
        {(isLoading || layoutBusy) && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70 z-10">
            <div className="flex items-center gap-2 text-stone-400 text-sm">
              <svg
                className="animate-spin w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              {layoutBusy ? "Computing layout..." : "Loading..."}
            </div>
          </div>
        )}

        {rfNodes.length > 0 ? (
          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.15, maxZoom: 1.5 }}
            minZoom={0.05}
            maxZoom={3}
            proOptions={{ hideAttribution: true }}
            defaultEdgeOptions={{ type: "smoothstep" }}
          >
            <Background color="#e7e5e4" gap={24} size={1} />
            <Controls
              style={{
                borderRadius: 10,
                border: "1px solid #d6d3d1",
                overflow: "hidden",
              }}
            />
            <MiniMap
              nodeColor={miniMapColor}
              style={{
                borderRadius: 10,
                border: "1px solid #d6d3d1",
                overflow: "hidden",
                height: 100,
                width: 160,
              }}
              pannable
              zoomable
            />
            <Panel position="bottom-left">
              <div className="bg-white/95 border border-stone-200 rounded-lg p-2 shadow-sm">
                <Legend
                  types={allEntityTypes}
                  active={filterTypes}
                  onToggle={toggleType}
                />
              </div>
            </Panel>
          </ReactFlow>
        ) : (
          !isLoading &&
          !layoutBusy && (
            <div className="flex items-center justify-center h-full">
              <p className="text-stone-400 text-sm">
                No nodes match the current filters.
              </p>
            </div>
          )
        )}
      </div>
    </div>
  );
}

// ── Exported page (wraps in ReactFlowProvider) ───────────────────────
export default function KnowledgeGraphPage() {
  return (
    <ReactFlowProvider>
      <KnowledgeGraphInner />
    </ReactFlowProvider>
  );
}
