/**
 * React Flow graph with collapsible component groups.
 *
 * Default view: each component is a single large node showing entity count
 * and type breakdown. Edges between groups show aggregate relationship counts.
 * Click a group to expand it and see individual entities.
 * Click the group header to collapse it back.
 */

import { useState, useCallback, useEffect, useMemo, memo } from "react";
import {
  ReactFlow,
  Background,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
  MarkerType,
  ReactFlowProvider,
  type Viewport,
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
  pipeline_stage: { bg: "#f5f5f4", border: "#a8a29e", text: "#57534e", icon: "S" },
  pipeline_job: { bg: "#f5f5f4", border: "#a8a29e", text: "#57534e", icon: "J" },
  pipeline_trigger: { bg: "#f5f5f4", border: "#a8a29e", text: "#57534e", icon: "T" },
  component: { bg: "#f5f5f4", border: "#a8a29e", text: "#57534e", icon: "#" },
};
const DEFAULT_PAL = { bg: "#f5f5f4", border: "#d6d3d1", text: "#57534e", icon: "?" };

const NODE_W = 260;
const NODE_H = 44;
const GROUP_NODE_W = 280;
const GROUP_NODE_H = 120;

// ── Entity node ──────────────────────────────────────────────────────
type EntityNodeData = { label: string; entityType: string; filePath: string };

const EntityNode = memo(({ data }: NodeProps<Node<EntityNodeData>>) => {
  const pal = TYPE_PALETTE[data.entityType] || DEFAULT_PAL;
  return (
    <div
      style={{
        background: pal.bg,
        border: `1.5px solid ${pal.border}`,
        borderRadius: 12,
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
        boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
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
      <span style={{ overflow: "hidden", textOverflow: "ellipsis" }} title={`${data.label}\n${data.filePath}`}>
        {data.label}
      </span>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
});
EntityNode.displayName = "EntityNode";

// ── Collapsed group node ─────────────────────────────────────────────
type CollapsedGroupData = {
  label: string;
  entityCount: number;
  typeCounts: Record<string, number>;
  onExpand: (groupName: string) => void;
};

const CollapsedGroupNode = memo(({ data }: NodeProps<Node<CollapsedGroupData>>) => {
  const topTypes = Object.entries(data.typeCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <div
      style={{
        width: GROUP_NODE_W,
        minHeight: GROUP_NODE_H,
        background: "#ffffff",
        border: "2px solid #d6d3d1",
        borderRadius: 16,
        padding: 0,
        cursor: "pointer",
        boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
        overflow: "hidden",
      }}
      onClick={() => data.onExpand(data.label)}
    >
      <Handle type="target" position={Position.Left} style={{ background: "#a8a29e", width: 8, height: 8 }} />
      {/* Header */}
      <div style={{
        padding: "10px 14px 8px",
        background: "#fafaf9",
        borderBottom: "1px solid #e7e5e4",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "#1c1917", letterSpacing: -0.3 }}>
          {data.label}
        </span>
        <span style={{
          fontSize: 10, fontWeight: 600, color: "#78716c",
          background: "#f5f5f4", borderRadius: 10, padding: "2px 8px",
        }}>
          {data.entityCount}
        </span>
      </div>
      {/* Type breakdown pills */}
      <div style={{ padding: "8px 12px 10px", display: "flex", flexWrap: "wrap", gap: 4 }}>
        {topTypes.map(([type, count]) => {
          const pal = TYPE_PALETTE[type] || DEFAULT_PAL;
          return (
            <span key={type} style={{
              fontSize: 10, padding: "2px 7px", borderRadius: 6,
              background: pal.bg, border: `1px solid ${pal.border}`,
              color: pal.text, fontWeight: 500,
            }}>
              {pal.icon} {count}
            </span>
          );
        })}
      </div>
      {/* Expand hint */}
      <div style={{
        padding: "4px 12px 8px", fontSize: 10, color: "#a8a29e",
        textAlign: "center",
      }}>
        Click to expand
      </div>
      <Handle type="source" position={Position.Right} style={{ background: "#a8a29e", width: 8, height: 8 }} />
    </div>
  );
});
CollapsedGroupNode.displayName = "CollapsedGroupNode";

// ── Expanded group background ────────────────────────────────────────
type GroupBgData = {
  label: string;
  width: number;
  height: number;
  onCollapse: (groupName: string) => void;
};

const GroupBgNode = memo(({ data }: NodeProps<Node<GroupBgData>>) => (
  <div
    style={{
      width: data.width,
      height: data.height,
      background: "rgba(250,250,249,0.6)",
      border: "1.5px dashed #d6d3d1",
      borderRadius: 16,
      pointerEvents: "none",
    }}
  >
    <div
      style={{
        padding: "8px 12px",
        fontSize: 11,
        fontWeight: 700,
        color: "#57534e",
        textTransform: "uppercase",
        letterSpacing: 0.5,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        pointerEvents: "auto",
        cursor: "pointer",
      }}
      onClick={() => data.onCollapse(data.label)}
    >
      <span>{data.label}</span>
      <span style={{
        fontSize: 9, color: "#a8a29e", fontWeight: 500,
        background: "#f5f5f4", borderRadius: 6, padding: "2px 8px",
        textTransform: "none", letterSpacing: 0,
      }}>
        Collapse
      </span>
    </div>
  </div>
));
GroupBgNode.displayName = "GroupBgNode";

const nodeTypes = { entity: EntityNode, collapsedGroup: CollapsedGroupNode, groupBg: GroupBgNode };

// ── ELK Layout ───────────────────────────────────────────────────────
const elk = new ELK();

const sanitizeId = (id: string) => id.replace(/[^a-zA-Z0-9_]/g, "_");

async function layoutNodes(
  nodes: Node[],
  edges: Edge[],
  direction: "RIGHT" | "DOWN",
): Promise<{ nodes: Node[]; edges: Edge[] }> {
  const elkNodes = nodes.map((n) => ({
    id: n.id,
    width: (n.data as any)?.width || (n.type === "collapsedGroup" ? GROUP_NODE_W : NODE_W),
    height: (n.data as any)?.height || (n.type === "collapsedGroup" ? GROUP_NODE_H : NODE_H),
  }));
  const elkEdges = edges.map((e) => ({
    id: `elk_${sanitizeId(e.id)}`,
    sources: [e.source],
    targets: [e.target],
  }));
  const graph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": direction,
      "elk.spacing.nodeNode": "40",
      "elk.layered.spacing.nodeNodeBetweenLayers": "120",
      "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
      "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
      "elk.edgeRouting": "SPLINES",
    },
    children: elkNodes,
    edges: elkEdges,
  };

  try {
    const result = await elk.layout(graph);
    const posMap = new Map<string, { x: number; y: number }>();
    for (const child of result.children || []) {
      posMap.set(child.id, { x: child.x || 0, y: child.y || 0 });
    }
    return {
      nodes: nodes.map((n) => ({ ...n, position: posMap.get(n.id) || { x: 0, y: 0 } })),
      edges,
    };
  } catch {
    let x = 0, y = 0;
    return {
      nodes: nodes.map((n, i) => {
        const pos = { x, y };
        x += 320;
        if ((i + 1) % 6 === 0) { x = 0; y += 180; }
        return { ...n, position: pos };
      }),
      edges,
    };
  }
}

async function layoutExpandedGroup(
  entityNodes: Node[],
  edges: Edge[],
  direction: "RIGHT" | "DOWN",
): Promise<{ nodes: Node[]; edges: Edge[]; width: number; height: number }> {
  const PAD = 24;
  const PAD_TOP = 44;
  const elkNodes = entityNodes.map((n) => ({
    id: sanitizeId(n.id),
    width: NODE_W,
    height: NODE_H,
  }));
  const idMap = new Map(entityNodes.map((n) => [sanitizeId(n.id), n.id]));
  const elkEdges = edges.map((e, i) => ({
    id: `ge_${i}`,
    sources: [sanitizeId(e.source)],
    targets: [sanitizeId(e.target)],
  }));
  const graph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": direction,
      "elk.spacing.nodeNode": "20",
      "elk.layered.spacing.nodeNodeBetweenLayers": "80",
      "elk.padding.top": String(PAD_TOP),
      "elk.padding.left": String(PAD),
      "elk.padding.bottom": String(PAD),
      "elk.padding.right": String(PAD),
      "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
      "elk.edgeRouting": "SPLINES",
    },
    children: elkNodes,
    edges: elkEdges,
  };

  try {
    const result = await elk.layout(graph);
    const posMap = new Map<string, { x: number; y: number }>();
    for (const child of result.children || []) {
      const origId = idMap.get(child.id) || child.id;
      posMap.set(origId, { x: child.x || 0, y: child.y || 0 });
    }
    return {
      nodes: entityNodes.map((n) => ({ ...n, position: posMap.get(n.id) || { x: 0, y: 0 } })),
      edges,
      width: ((result as any).width || 400) + PAD * 2,
      height: ((result as any).height || 200) + PAD_TOP + PAD,
    };
  } catch {
    const cols = Math.ceil(Math.sqrt(entityNodes.length));
    return {
      nodes: entityNodes.map((n, i) => ({
        ...n,
        position: { x: PAD + (i % cols) * (NODE_W + 20), y: PAD_TOP + Math.floor(i / cols) * (NODE_H + 16) },
      })),
      edges,
      width: PAD * 2 + cols * (NODE_W + 20),
      height: PAD_TOP + PAD + Math.ceil(entityNodes.length / cols) * (NODE_H + 16),
    };
  }
}

// ── Build collapsed/expanded elements ────────────────────────────────
interface GroupInfo {
  name: string;
  nodeIds: Set<string>;
  typeCounts: Record<string, number>;
}

function buildGroupData(
  apiNodes: ApiGraphNode[],
  _apiEdges: ApiGraphEdge[],
): { groups: GroupInfo[]; nodeToGroup: Map<string, string> } {
  const nodeToGroup = new Map<string, string>();
  const groupMap = new Map<string, GroupInfo>();

  for (const n of apiNodes) {
    const comp = (n.properties?.component as string) || "";
    const groupName = comp || deriveGroup(n);
    nodeToGroup.set(n.id, groupName);
    if (!groupMap.has(groupName)) {
      groupMap.set(groupName, { name: groupName, nodeIds: new Set(), typeCounts: {} });
    }
    const g = groupMap.get(groupName)!;
    g.nodeIds.add(n.id);
    const et = (n.properties?.entity_type as string) || "unknown";
    g.typeCounts[et] = (g.typeCounts[et] || 0) + 1;
  }

  // If everything landed in one group, split by entity type instead
  const groups = [...groupMap.values()];
  if (groups.length <= 1 && apiNodes.length > 20) {
    groupMap.clear();
    nodeToGroup.clear();
    for (const n of apiNodes) {
      const et = (n.properties?.entity_type as string) || "other";
      const groupName = TYPE_GROUP_LABELS[et] || "Other";
      nodeToGroup.set(n.id, groupName);
      if (!groupMap.has(groupName)) {
        groupMap.set(groupName, { name: groupName, nodeIds: new Set(), typeCounts: {} });
      }
      const g = groupMap.get(groupName)!;
      g.nodeIds.add(n.id);
      g.typeCounts[et] = (g.typeCounts[et] || 0) + 1;
    }
    return { groups: [...groupMap.values()], nodeToGroup };
  }

  return { groups, nodeToGroup };
}

/** Derive a group name from file path when component metadata is missing */
function deriveGroup(n: ApiGraphNode): string {
  const fp = (n.properties?.file_path as string) || "";
  if (!fp) return "ungrouped";
  const parts = fp.split("/").filter(Boolean);
  if (parts.length <= 1) return "root";
  // Use first meaningful directory (skip common src dirs)
  const skip = new Set(["src", "lib", "app", "pkg", "internal"]);
  const first = parts[0];
  if (skip.has(first) && parts.length > 2) return parts[1];
  return first;
}

const TYPE_GROUP_LABELS: Record<string, string> = {
  class: "Classes",
  model: "Models",
  function: "Functions",
  method: "Methods",
  endpoint: "Endpoints",
  db_read: "Database Reads",
  db_write: "Database Writes",
  file_reader: "File Readers",
  file_writer: "File Writers",
  consumer: "Consumers",
  producer: "Producers",
  variable: "Variables",
  pipeline_stage: "Pipeline Stages",
  pipeline_job: "Pipeline Jobs",
  pipeline_trigger: "Pipeline Triggers",
  component: "Components",
};

function buildCollapsedView(
  groups: GroupInfo[],
  apiEdges: ApiGraphEdge[],
  nodeToGroup: Map<string, string>,
  onExpand: (name: string) => void,
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = groups.map((g) => ({
    id: `group_${sanitizeId(g.name)}`,
    type: "collapsedGroup",
    data: {
      label: g.name,
      entityCount: g.nodeIds.size,
      typeCounts: g.typeCounts,
      onExpand,
    },
    position: { x: 0, y: 0 },
  }));

  // Aggregate edges between groups
  const edgeCounts = new Map<string, number>();
  for (const e of apiEdges) {
    const sg = nodeToGroup.get(e.source) || "ungrouped";
    const tg = nodeToGroup.get(e.target) || "ungrouped";
    if (sg !== tg) {
      const key = `group_${sanitizeId(sg)}->group_${sanitizeId(tg)}`;
      edgeCounts.set(key, (edgeCounts.get(key) || 0) + 1);
    }
  }

  const edges: Edge[] = [...edgeCounts.entries()].map(([key, count], i) => {
    const [source, target] = key.split("->");
    return {
      id: `ge_${i}`,
      source,
      target,
      label: String(count),
      type: "default",
      style: { stroke: "#78716c", strokeWidth: Math.min(1 + count * 0.3, 4) },
      labelStyle: { fontSize: 11, fill: "#57534e", fontWeight: 600 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#78716c", width: 16, height: 16 },
    };
  });

  return { nodes, edges };
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
            className="text-[10px] px-1.5 py-0.5 rounded-md"
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
    <div className="absolute inset-0 flex items-center justify-center bg-white/80 backdrop-blur-sm z-10">
      <div className="flex items-center gap-2.5 text-stone-500 text-sm font-medium">
        <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
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
  height = "600px",
  direction: initialDirection = "RIGHT",
  showDirectionToggle = true,
  showMiniMap = true,
  emptyMessage = "No entities to display.",
}: FlowGraphProps) {
  const [direction, setDirection] = useState(initialDirection);
  const [layoutBusy, setLayoutBusy] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  const { fitView, zoomIn, zoomOut } = useReactFlow();

  const [rfNodes, setRfNodes, onNodesChange] = useNodesState<Node>([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const { groups, nodeToGroup } = useMemo(
    () => buildGroupData(apiNodes, apiEdges),
    [apiNodes, apiEdges],
  );

  const allEntityTypes = useMemo(() => {
    const types = new Set<string>();
    for (const n of apiNodes) types.add((n.properties?.entity_type as string) || n.type);
    return [...types].sort();
  }, [apiNodes]);

  const totalEntities = apiNodes.length;
  const totalEdges = apiEdges.length;

  const handleExpand = useCallback((name: string) => {
    setExpandedGroups((prev) => { const next = new Set(prev); next.add(name); return next; });
  }, []);

  const handleCollapse = useCallback((name: string) => {
    setExpandedGroups((prev) => { const next = new Set(prev); next.delete(name); return next; });
  }, []);

  const handleExpandAll = useCallback(() => {
    setExpandedGroups(new Set(groups.map((g) => g.name)));
  }, [groups]);

  const handleCollapseAll = useCallback(() => {
    setExpandedGroups(new Set());
  }, []);

  // Build and layout graph whenever expansion state changes
  useEffect(() => {
    if (apiNodes.length === 0) {
      setRfNodes([]); setRfEdges([]);
      return;
    }

    setLayoutBusy(true);

    const run = async () => {
      // Only show flat view for very small graphs (no need for grouping)
      const useFlat = apiNodes.length <= 20;

      if (useFlat || (expandedGroups.size === groups.length)) {
        // Full expanded view — all entities
        const allNodes: Node[] = apiNodes.map((n) => ({
          id: n.id,
          type: "entity",
          data: {
            label: n.label,
            entityType: (n.properties?.entity_type as string) || "class",
            filePath: (n.properties?.file_path as string) || "",
          },
          position: { x: 0, y: 0 },
        }));
        const idSet = new Set(allNodes.map((n) => n.id));
        const allEdges: Edge[] = apiEdges
          .filter((e) => idSet.has(e.source) && idSet.has(e.target))
          .map((e, i) => ({
            id: `e_${i}`,
            source: e.source,
            target: e.target,
            label: e.type,
            type: "default",
            animated: e.type === "CALLS" || e.type === "calls",
            style: { stroke: "#a8a29e", strokeWidth: 1.5, ...(e.type === "uses" || e.type === "USES" ? { strokeDasharray: "4 2" } : {}) },
            labelStyle: { fontSize: 9, fill: "#78716c" },
            markerEnd: { type: MarkerType.ArrowClosed, color: "#a8a29e", width: 14, height: 14 },
          }));

        const laid = await layoutNodes(allNodes, allEdges, direction);
        setRfNodes(laid.nodes);
        setRfEdges(laid.edges);
      } else if (expandedGroups.size === 0) {
        // All collapsed — show group overview
        const { nodes, edges } = buildCollapsedView(groups, apiEdges, nodeToGroup, handleExpand);
        const laid = await layoutNodes(nodes, edges, direction);
        setRfNodes(laid.nodes);
        setRfEdges(laid.edges);
      } else {
        // Mixed: some expanded, some collapsed
        const resultNodes: Node[] = [];
        const resultEdges: Edge[] = [];

        // Collapsed groups
        for (const g of groups) {
          if (expandedGroups.has(g.name)) continue;
          resultNodes.push({
            id: `group_${sanitizeId(g.name)}`,
            type: "collapsedGroup",
            data: { label: g.name, entityCount: g.nodeIds.size, typeCounts: g.typeCounts, onExpand: handleExpand },
            position: { x: 0, y: 0 },
          });
        }

        // Expanded groups — layout internally, then place as a unit
        for (const g of groups) {
          if (!expandedGroups.has(g.name)) continue;
          const groupEntities = apiNodes.filter((n) => g.nodeIds.has(n.id));
          const groupEntityNodes: Node[] = groupEntities.map((n) => ({
            id: n.id,
            type: "entity",
            data: {
              label: n.label,
              entityType: (n.properties?.entity_type as string) || "class",
              filePath: (n.properties?.file_path as string) || "",
            },
            position: { x: 0, y: 0 },
          }));
          const groupEntityIds = new Set(groupEntities.map((n) => n.id));
          const internalEdges: Edge[] = apiEdges
            .filter((e) => groupEntityIds.has(e.source) && groupEntityIds.has(e.target))
            .map((e, i) => ({
              id: `${g.name}_e_${i}`,
              source: e.source,
              target: e.target,
              type: "default",
              style: { stroke: "#a8a29e", strokeWidth: 1.2 },
              markerEnd: { type: MarkerType.ArrowClosed, color: "#a8a29e", width: 12, height: 12 },
            }));

          const laid = await layoutExpandedGroup(groupEntityNodes, internalEdges, direction);

          // Add background node
          resultNodes.push({
            id: `groupbg_${sanitizeId(g.name)}`,
            type: "groupBg",
            data: { label: g.name, width: laid.width, height: laid.height, onCollapse: handleCollapse },
            position: { x: 0, y: 0 },
            zIndex: -1,
            selectable: false,
            draggable: false,
            connectable: false,
            focusable: false,
          });

          // Add entity nodes (positions relative, will be offset after top-level layout)
          for (const n of laid.nodes) {
            resultNodes.push({ ...n, data: { ...n.data, _groupBg: `groupbg_${sanitizeId(g.name)}` } });
          }
          resultEdges.push(...laid.edges);
        }

        // Add inter-group edges
        const edgeCounts = new Map<string, number>();
        for (const e of apiEdges) {
          const sg = nodeToGroup.get(e.source) || "ungrouped";
          const tg = nodeToGroup.get(e.target) || "ungrouped";
          if (sg === tg) continue;
          const sId = expandedGroups.has(sg) ? e.source : `group_${sanitizeId(sg)}`;
          const tId = expandedGroups.has(tg) ? e.target : `group_${sanitizeId(tg)}`;
          const key = `${sId}>${tId}`;
          if (!edgeCounts.has(key)) {
            edgeCounts.set(key, 0);
            resultEdges.push({
              id: `cross_${resultEdges.length}`,
              source: sId,
              target: tId,
              type: "default",
              style: { stroke: "#78716c", strokeWidth: 1.5 },
              markerEnd: { type: MarkerType.ArrowClosed, color: "#78716c", width: 14, height: 14 },
            });
          }
          edgeCounts.set(key, edgeCounts.get(key)! + 1);
        }

        // Top-level layout for collapsed groups + expanded group backgrounds
        const topLevelNodes = resultNodes.filter(
          (n) => n.type === "collapsedGroup" || n.type === "groupBg",
        );
        const topLevelEdges = resultEdges.filter((e) =>
          topLevelNodes.some((n) => n.id === e.source) || topLevelNodes.some((n) => n.id === e.target),
        );

        const topLaid = await layoutNodes(topLevelNodes, topLevelEdges, direction);
        const topPosMap = new Map(topLaid.nodes.map((n) => [n.id, n.position]));

        // Offset entity nodes by their group background position
        const finalNodes = resultNodes.map((n) => {
          if (n.type === "collapsedGroup" || n.type === "groupBg") {
            return { ...n, position: topPosMap.get(n.id) || n.position };
          }
          // Entity node — offset by its parent groupBg position
          const bgId = (n.data as any)?._groupBg;
          if (bgId) {
            const bgPos = topPosMap.get(bgId) || { x: 0, y: 0 };
            return { ...n, position: { x: bgPos.x + n.position.x, y: bgPos.y + n.position.y } };
          }
          return n;
        });

        setRfNodes(finalNodes);
        setRfEdges(resultEdges);
      }

      setLayoutBusy(false);
      requestAnimationFrame(() => {
        fitView({ padding: 0.12, maxZoom: 1.0, duration: 350 });
      });
    };

    run();
  }, [apiNodes, apiEdges, groups, nodeToGroup, expandedGroups, direction, handleExpand, handleCollapse, fitView, setRfNodes, setRfEdges]);

  const onViewportChange = useCallback((viewport: Viewport) => {
    setZoomLevel(viewport.zoom);
  }, []);

  const miniMapColor = useCallback((node: Node) => {
    if (node.type === "collapsedGroup") return "#78716c";
    const et = (node.data?.entityType as string) || "";
    return (TYPE_PALETTE[et] || DEFAULT_PAL).border;
  }, []);

  const expandedCount = expandedGroups.size;

  return (
    <div className="flex flex-col" style={{ height }}>
      <div className="flex items-center justify-between mb-2 flex-shrink-0 px-1">
        <div className="flex items-center gap-3 text-xs text-stone-500">
          <span className="font-medium text-stone-700">{totalEntities} entities</span>
          <span>{totalEdges} relationships</span>
          <span>{groups.length} components</span>
          {expandedCount > 0 && (
            <span className="text-emerald-600 font-medium">{expandedCount} expanded</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {groups.length > 1 && (
            <div className="flex items-center gap-1">
              <button
                onClick={handleCollapseAll}
                className={`text-xs px-2.5 py-1 rounded-lg transition-colors ${expandedCount === 0 ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-500 hover:bg-stone-200"}`}
              >
                Overview
              </button>
              <button
                onClick={handleExpandAll}
                className={`text-xs px-2.5 py-1 rounded-lg transition-colors ${expandedCount === groups.length ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-500 hover:bg-stone-200"}`}
              >
                All Entities
              </button>
            </div>
          )}
          {showDirectionToggle && (
            <>
              <div className="w-px h-4 bg-stone-200" />
              <button onClick={() => setDirection("RIGHT")}
                className={`text-xs px-2 py-1 rounded-lg transition-colors ${direction === "RIGHT" ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-500"}`}>
                Horizontal
              </button>
              <button onClick={() => setDirection("DOWN")}
                className={`text-xs px-2 py-1 rounded-lg transition-colors ${direction === "DOWN" ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-500"}`}>
                Vertical
              </button>
            </>
          )}
        </div>
      </div>
      <div className="flex-1 bg-white border border-stone-200/60 rounded-2xl overflow-hidden relative min-h-0 shadow-sm">
        {(isLoading || layoutBusy) && <Spinner text={layoutBusy ? "Computing layout..." : "Loading..."} />}
        {rfNodes.length > 0 ? (
          <ReactFlow
            nodes={rfNodes} edges={rfEdges}
            onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes} fitView
            fitViewOptions={{ padding: 0.12, maxZoom: 1.0 }}
            minZoom={0.15} maxZoom={3}
            zoomOnScroll={true}
            panOnScroll={false}
            onViewportChange={onViewportChange}
            proOptions={{ hideAttribution: true }}
            defaultEdgeOptions={{ type: "smoothstep" }}
          >
            <Background color="#e7e5e4" gap={20} size={1} />
            {showMiniMap && (
              <MiniMap nodeColor={miniMapColor}
                style={{ borderRadius: 12, border: "1px solid #e7e5e4", overflow: "hidden", height: 90, width: 150, background: "#fafaf9" }}
                pannable zoomable />
            )}
            <Panel position="top-right">
              <div className="bg-white/95 backdrop-blur-sm border border-stone-200/60 rounded-xl shadow-sm flex items-center gap-1 p-1">
                <button onClick={() => zoomOut()} className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-stone-100 text-stone-400 transition-colors" title="Zoom Out">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="5" y1="12" x2="19" y2="12"/></svg>
                </button>
                <span className="text-[10px] text-stone-400 w-9 text-center font-mono">{Math.round(zoomLevel * 100)}%</span>
                <button onClick={() => zoomIn()} className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-stone-100 text-stone-400 transition-colors" title="Zoom In">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                </button>
                <div className="w-px h-4 bg-stone-200 mx-0.5" />
                <button onClick={() => fitView({ padding: 0.12, maxZoom: 1.0, duration: 300 })} className="h-7 px-2 flex items-center justify-center rounded-lg hover:bg-stone-100 text-stone-400 text-[10px] font-semibold transition-colors" title="Fit to View">
                  Fit
                </button>
              </div>
            </Panel>
            <Panel position="bottom-left">
              <div className="bg-white/95 backdrop-blur-sm border border-stone-200/60 rounded-xl p-2 shadow-sm">
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
