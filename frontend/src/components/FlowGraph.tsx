/**
 * React Flow graph with ELK hierarchical layout and visual component grouping.
 *
 * Grouping approach:
 *  - ELK handles layout with hierarchical groups (component-based)
 *  - After layout, group bounding boxes become background rectangles
 *  - Entity nodes use ABSOLUTE positions (no parentId) so edges route correctly
 *  - Group nodes are zIndex:-1, non-interactive, no handles — purely decorative
 */

import { useState, useCallback, useEffect, useMemo, memo } from "react";
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
import type { GraphNode as ApiGraphNode, GraphEdge as ApiGraphEdge } from "../api/client";

// ── Palette ──────────────────────────────────────────────────────────
export const TYPE_PALETTE: Record<
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
  file_reader: { bg: "#f0fdf4", border: "#4ade80", text: "#166534", icon: "\u2190" },
  file_writer: { bg: "#fff1f2", border: "#fb7185", text: "#9f1239", icon: "\u2192" },
  db_read: { bg: "#eff6ff", border: "#3b82f6", text: "#1e3a5f", icon: "\u25B7" },
  db_write: { bg: "#fef2f2", border: "#ef4444", text: "#991b1b", icon: "\u25C1" },
};
const DEFAULT_PAL = { bg: "#f5f5f4", border: "#d6d3d1", text: "#57534e", icon: "?" };

const NODE_W = 200;
const NODE_H = 36;

// ── Entity node ──────────────────────────────────────────────────────
type EntityNodeData = { label: string; entityType: string; filePath: string };

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
        width: NODE_W,
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <span
        style={{
          width: 18, height: 18, borderRadius: 4,
          background: pal.border + "40",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 10, fontWeight: 700, flexShrink: 0,
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

// ── Group background node (decorative only) ──────────────────────────
type GroupNodeData = { label: string; width: number; height: number };

const GroupNode = memo(({ data }: NodeProps<Node<GroupNodeData>>) => (
  <div
    style={{
      width: data.width,
      height: data.height,
      background: "rgba(250,250,249,0.7)",
      border: "1.5px dashed #d6d3d1",
      borderRadius: 12,
      pointerEvents: "none",
    }}
  >
    <div
      style={{
        padding: "6px 10px",
        fontSize: 10,
        fontWeight: 600,
        color: "#78716c",
        textTransform: "uppercase",
        letterSpacing: 0.5,
      }}
    >
      {data.label}
    </div>
  </div>
));
GroupNode.displayName = "GroupNode";

const nodeTypes = { entity: EntityNode, group: GroupNode };

// ── ELK layout ───────────────────────────────────────────────────────
const elk = new ELK();
const GROUP_PAD_TOP = 28;
const GROUP_PAD = 14;

async function elkLayout(
  entityNodes: Node[],
  edges: Edge[],
  direction: "RIGHT" | "DOWN" = "RIGHT"
): Promise<{ nodes: Node[]; edges: Edge[] }> {
  // Build group membership
  const groupOf = new Map<string, string>();
  for (const n of entityNodes) {
    groupOf.set(n.id, (n.data?.component as string) || "");
  }

  // Collect unique groups (skip empty = ungrouped)
  const groupNames = [...new Set(groupOf.values())].filter(Boolean).sort();
  const hasGroups = groupNames.length > 0;

  // ELK can crash if IDs contain special characters like :, @, #, etc.
  const sanitizeId = (id: string) => id.replace(/[^a-zA-Z0-9_]/g, "_");
  const elkIdToOriginal = new Map<string, string>();

  // If there are groups, use ELK hierarchical layout
  if (hasGroups) {
    const groupIds = new Map<string, string[]>();
    const ungrouped: string[] = [];
    for (const n of entityNodes) {
      const g = groupOf.get(n.id) || "";
      if (g) {
        if (!groupIds.has(g)) groupIds.set(g, []);
        groupIds.get(g)!.push(n.id);
      } else {
        ungrouped.push(n.id);
      }
    }

    const allGroupNodeIds = new Set<string>();
    for (const ids of groupIds.values()) ids.forEach((id) => allGroupNodeIds.add(id));

    const elkGroups = [...groupIds.entries()].map(([gname, ids]) => ({
      id: `elkgrp_${sanitizeId(gname)}`,
      layoutOptions: {
        "elk.algorithm": "layered",
        "elk.direction": direction,
        "elk.spacing.nodeNode": "24",
        "elk.layered.spacing.nodeNodeBetweenLayers": "50",
        "elk.padding.top": String(GROUP_PAD_TOP + GROUP_PAD),
        "elk.padding.left": String(GROUP_PAD),
        "elk.padding.bottom": String(GROUP_PAD),
        "elk.padding.right": String(GROUP_PAD),
      },
      children: ids.map((id) => {
        const sId = `elk_${sanitizeId(id)}`;
        elkIdToOriginal.set(sId, id);
        return { id: sId, width: NODE_W, height: NODE_H };
      }),
      edges: edges
        .filter((e) => ids.includes(e.source) && ids.includes(e.target))
        .map((e) => ({
          id: `elkedge_${sanitizeId(e.id)}`,
          sources: [`elk_${sanitizeId(e.source)}`],
          targets: [`elk_${sanitizeId(e.target)}`]
        })),
    }));

    // Ungrouped nodes go at root level
    const rootChildren: any[] = [...elkGroups];
    for (const id of ungrouped) {
      const sId = `elk_${sanitizeId(id)}`;
      elkIdToOriginal.set(sId, id);
      rootChildren.push({ id: sId, width: NODE_W, height: NODE_H });
    }

    // Cross-group + ungrouped edges
    const crossEdges = edges
      .filter((e) => {
        const sg = groupOf.get(e.source) || "";
        const tg = groupOf.get(e.target) || "";
        return sg !== tg;
      })
      .map((e) => ({
        id: `cross_${sanitizeId(e.id)}`,
        sources: [`elk_${sanitizeId(e.source)}`],
        targets: [`elk_${sanitizeId(e.target)}`]
      }));

    const graph = {
      id: "root",
      layoutOptions: {
        "elk.algorithm": "layered",
        "elk.direction": direction,
        "elk.spacing.nodeNode": "30",
        "elk.layered.spacing.nodeNodeBetweenLayers": "80",
        "elk.hierarchyHandling": "INCLUDE_CHILDREN",
        "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
        "elk.edgeRouting": "POLYLINE",
      },
      children: rootChildren,
      edges: crossEdges,
    };

    try {
      const result = await elk.layout(graph);

      // Extract absolute positions for all entity nodes
      const posMap = new Map<string, { x: number; y: number }>();
      const groupBounds = new Map<string, { x: number; y: number; w: number; h: number }>();

      for (const child of result.children || []) {
        const cx = child.x || 0;
        const cy = child.y || 0;

        if (child.id.startsWith("elkgrp_")) {
          // This is a group — record its bounds and compute child absolute positions
          // Warning: gname from id is sanitized!
          // Match it with the exact raw group name from our loop earlier (via loop index or mapping).
          // But since group bounds are decorative, we just reconstruct the name from the child id hack:
          let gname = child.id.slice("elkgrp_".length);
          // Let's actually look up the exact gname since sanitizeId could produce collisions mostly
          // We'll just search our groups:
          const realNameMatch = groupNames.find((n) => sanitizeId(n) === gname) || gname;
          
          groupBounds.set(realNameMatch, {
            x: cx, y: cy,
            w: child.width || 300, h: child.height || 200,
          });
          for (const gc of child.children || []) {
            const origId = elkIdToOriginal.get(gc.id);
            if (origId) posMap.set(origId, { x: cx + (gc.x || 0), y: cy + (gc.y || 0) });
          }
        } else {
          // Ungrouped node at root
          const origId = elkIdToOriginal.get(child.id);
          if (origId) posMap.set(origId, { x: cx, y: cy });
        }
      }

      // Build entity nodes with absolute positions (NO parentId)
      const positioned: Node[] = entityNodes.map((n) => ({
        ...n,
        position: posMap.get(n.id) || { x: 0, y: 0 },
      }));

      // Build group background nodes from ELK group bounds
      const bgNodes: Node[] = [];
      for (const [gname, b] of groupBounds) {
        bgNodes.push({
          id: `groupbg_${gname}`,
          type: "group",
          position: { x: b.x, y: b.y },
          data: { label: gname, width: b.w, height: b.h },
          zIndex: -1,
          selectable: false,
          draggable: false,
          connectable: false,
          focusable: false,
        });
      }

      return { nodes: [...bgNodes, ...positioned], edges };
    } catch {
      // Fall through to flat layout
    }
  }

  // Flat layout (no groups or fallback)
  const graph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": direction,
      "elk.spacing.nodeNode": "30",
      "elk.layered.spacing.nodeNodeBetweenLayers": "80",
      "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
      "elk.edgeRouting": "POLYLINE",
    },
    children: entityNodes.map((n) => ({ id: n.id, width: NODE_W, height: NODE_H })),
    edges: edges.map((e) => ({
      id: `elk_${e.id}`,
      sources: [e.source],
      targets: [e.target],
    })),
  };

  try {
    const result = await elk.layout(graph);
    const posMap = new Map<string, { x: number; y: number }>();
    for (const child of result.children || []) {
      posMap.set(child.id, { x: child.x || 0, y: child.y || 0 });
    }
    return {
      nodes: entityNodes.map((n) => ({
        ...n,
        position: posMap.get(n.id) || { x: 0, y: 0 },
      })),
      edges,
    };
  } catch {
    let x = 0, y = 0;
    return {
      nodes: entityNodes.map((n, i) => {
        const pos = { x, y };
        x += NODE_W + 40;
        if ((i + 1) % 8 === 0) { x = 0; y += NODE_H + 30; }
        return { ...n, position: pos };
      }),
      edges,
    };
  }
}

// ── Build elements ──────────────────────────────────────────────────
function buildElements(
  apiNodes: ApiGraphNode[],
  apiEdges: ApiGraphEdge[],
  maxNodes: number
): { nodes: Node[]; edges: Edge[]; total: number; shown: number } {
  const total = apiNodes.length;
  const display = apiNodes.slice(0, maxNodes);
  const shown = display.length;
  const idSet = new Set(display.map((n) => n.id));

  const nodes: Node[] = display.map((n) => {
    const et = (n.properties?.entity_type as string) || "class";
    const component = (n.properties?.component as string) || "";
    return {
      id: n.id,
      type: "entity",
      data: {
        label: n.label,
        entityType: et,
        filePath: (n.properties?.file_path as string) || "",
        component,
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
      markerEnd: { type: MarkerType.ArrowClosed, color: "#a8a29e", width: 12, height: 12 },
    }));

  return { nodes, edges, total, shown };
}

// ── Legend ────────────────────────────────────────────────────────────
function Legend({ types }: { types: string[] }) {
  return (
    <div className="flex flex-wrap gap-1">
      {types.map((t) => {
        const pal = TYPE_PALETTE[t] || DEFAULT_PAL;
        return (
          <span
            key={t}
            className="text-[10px] px-1.5 py-0.5 rounded"
            style={{ background: pal.bg, border: `1px solid ${pal.border}`, color: pal.text }}
          >
            {pal.icon} {t}
          </span>
        );
      })}
    </div>
  );
}

function Spinner({ text }: { text: string }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-white/70 z-10">
      <div className="flex items-center gap-2 text-stone-400 text-sm">
        <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {text}
      </div>
    </div>
  );
}

// ── Props ────────────────────────────────────────────────────────────
export interface FlowGraphProps {
  nodes: ApiGraphNode[];
  edges: ApiGraphEdge[];
  isLoading?: boolean;
  height?: string;
  maxNodes?: number;
  direction?: "RIGHT" | "DOWN";
  showDirectionToggle?: boolean;
  showMiniMap?: boolean;
  emptyMessage?: string;
}

function FlowGraphInner({
  nodes: apiNodes,
  edges: apiEdges,
  isLoading = false,
  height = "500px",
  maxNodes = 200,
  direction: initialDirection = "RIGHT",
  showDirectionToggle = true,
  showMiniMap = true,
  emptyMessage = "No entities to display.",
}: FlowGraphProps) {
  const [direction, setDirection] = useState(initialDirection);
  const [layoutBusy, setLayoutBusy] = useState(false);

  const [rfNodes, setRfNodes, onNodesChange] = useNodesState<Node>([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [info, setInfo] = useState({ total: 0, shown: 0 });

  const allEntityTypes = useMemo(() => {
    const types = new Set<string>();
    for (const n of apiNodes) {
      types.add((n.properties?.entity_type as string) || n.type);
    }
    return [...types].sort();
  }, [apiNodes]);

  useEffect(() => {
    if (apiNodes.length === 0) {
      setRfNodes([]); setRfEdges([]); setInfo({ total: 0, shown: 0 });
      return;
    }
    const { nodes, edges, total, shown } = buildElements(apiNodes, apiEdges, maxNodes);
    if (nodes.length === 0) {
      setRfNodes([]); setRfEdges([]); setInfo({ total, shown: 0 });
      return;
    }
    setInfo({ total, shown });
    setLayoutBusy(true);
    elkLayout(nodes, edges, direction).then(({ nodes: ln, edges: le }) => {
      setRfNodes(ln); setRfEdges(le); setLayoutBusy(false);
    });
  }, [apiNodes, apiEdges, maxNodes, direction, setRfNodes, setRfEdges]);

  const miniMapColor = useCallback((node: Node) => {
    const et = (node.data?.entityType as string) || "";
    return (TYPE_PALETTE[et] || DEFAULT_PAL).border;
  }, []);

  return (
    <div className="flex flex-col" style={{ height }}>
      {(showDirectionToggle || info.total > 0) && (
        <div className="flex items-center justify-between mb-2 flex-shrink-0 px-1">
          <div className="flex items-center gap-2 text-xs text-stone-400">
            <span>{info.shown} entities</span>
            {info.total > info.shown && <span className="text-amber-600">of {info.total}</span>}
            <span>{rfEdges.length} relationships</span>
          </div>
          {showDirectionToggle && (
            <div className="flex items-center gap-1">
              <button onClick={() => setDirection("RIGHT")}
                className={`text-xs px-2 py-0.5 rounded-md ${direction === "RIGHT" ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-500"}`}>
                Horizontal
              </button>
              <button onClick={() => setDirection("DOWN")}
                className={`text-xs px-2 py-0.5 rounded-md ${direction === "DOWN" ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-500"}`}>
                Vertical
              </button>
            </div>
          )}
        </div>
      )}
      <div className="flex-1 bg-white border border-stone-200 rounded-xl overflow-hidden relative min-h-0">
        {(isLoading || layoutBusy) && <Spinner text={layoutBusy ? "Computing layout..." : "Loading..."} />}
        {rfNodes.length > 0 ? (
          <ReactFlow
            nodes={rfNodes} edges={rfEdges}
            onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes} fitView
            fitViewOptions={{ padding: 0.15, maxZoom: 1.5 }}
            minZoom={0.05} maxZoom={3}
            proOptions={{ hideAttribution: true }}
            defaultEdgeOptions={{ type: "smoothstep" }}
          >
            <Background color="#e7e5e4" gap={24} size={1} />
            <Controls style={{ borderRadius: 10, border: "1px solid #d6d3d1", overflow: "hidden" }} />
            {showMiniMap && (
              <MiniMap nodeColor={miniMapColor}
                style={{ borderRadius: 10, border: "1px solid #d6d3d1", overflow: "hidden", height: 80, width: 140 }}
                pannable zoomable />
            )}
            <Panel position="bottom-left">
              <div className="bg-white/95 border border-stone-200 rounded-lg p-1.5 shadow-sm">
                <Legend types={allEntityTypes} />
              </div>
            </Panel>
          </ReactFlow>
        ) : (
          !isLoading && !layoutBusy && (
            <div className="flex items-center justify-center h-full">
              <p className="text-stone-400 text-sm">{emptyMessage}</p>
            </div>
          )
        )}
      </div>
    </div>
  );
}

export default function FlowGraph(props: FlowGraphProps) {
  return (
    <ReactFlowProvider>
      <FlowGraphInner {...props} />
    </ReactFlowProvider>
  );
}
