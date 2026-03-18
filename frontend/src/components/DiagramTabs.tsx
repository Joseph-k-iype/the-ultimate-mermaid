import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type DataManifest, type ManifestEntity } from "../api/client";
import FlowGraph from "./FlowGraph";
import MermaidRenderer from "./MermaidRenderer";
import PublishPatternModal from "./PublishPatternModal";

const DIAGRAM_TABS = [
  { id: "er", label: "ER Diagram", direction: "RIGHT" as const },
  { id: "dataflow", label: "Data Flow", direction: "RIGHT" as const },
];


const CATEGORY_LABELS: Record<string, string> = {
  data_models: "Data Models",
  endpoints: "API Endpoints",
  data_stores: "Data Stores",
  file_io: "File I/O",
  messaging: "Messaging",
  processing: "Processing",
};

type ViewMode = "graph" | "mermaid";

interface DiagramTabsProps {
  scanId: string;
  perspectives?: string[];
  components?: string[];
}

// ── Manifest entity row ──────────────────────────────────────────────
function EntityRow({ entity }: { entity: ManifestEntity }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-stone-100 last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left px-3 py-2 flex items-center gap-2 hover:bg-stone-50 text-sm"
      >
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-stone-100 text-stone-500 font-mono">
          {entity.type}
        </span>
        <span className="font-medium text-stone-800">{entity.name}</span>
        <span className="text-stone-400 text-xs ml-auto truncate max-w-[200px]">
          {entity.location.file}:{entity.location.line}
        </span>
        <span className="text-stone-300 text-xs">{open ? "\u25B2" : "\u25BC"}</span>
      </button>
      {open && (
        <div className="px-4 pb-3 text-xs space-y-2 bg-stone-50/50">
          {entity.schema && entity.schema.fields.length > 0 && (
            <div>
              <p className="font-medium text-stone-500 mb-1">Fields</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
                {entity.schema.fields.map((f, i) => (
                  <div key={i} className="flex gap-1">
                    <span className="text-stone-700">{f.name}</span>
                    <span className="text-stone-400">{f.type}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {entity.methods && entity.methods.length > 0 && (
            <div>
              <p className="font-medium text-stone-500 mb-1">Methods</p>
              <div className="flex flex-wrap gap-1">
                {entity.methods.map((m) => (
                  <span key={m} className="px-1.5 py-0.5 bg-stone-100 rounded text-stone-600 font-mono">
                    {m}()
                  </span>
                ))}
              </div>
            </div>
          )}
          {entity.http_method && (
            <div>
              <span className="font-medium text-stone-500">Route: </span>
              <span className="font-mono text-stone-700">
                {entity.http_method.toUpperCase()} {entity.route}
              </span>
            </div>
          )}
          {entity.lineage && (
            <div>
              {entity.lineage.downstream && entity.lineage.downstream.length > 0 && (
                <div>
                  <span className="font-medium text-stone-500">Downstream: </span>
                  {entity.lineage.downstream.map((d, i) => (
                    <span key={i} className="text-stone-600">
                      {i > 0 && ", "}
                      {d.target.split("::").pop()} ({d.type})
                    </span>
                  ))}
                </div>
              )}
              {entity.lineage.upstream && entity.lineage.upstream.length > 0 && (
                <div>
                  <span className="font-medium text-stone-500">Upstream: </span>
                  {entity.lineage.upstream.map((u, i) => (
                    <span key={i} className="text-stone-600">
                      {i > 0 && ", "}
                      {u.source.split("::").pop()} ({u.type})
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Business-friendly manifest view ──────────────────────────────────
function ManifestBusinessView({ manifest }: { manifest: DataManifest }) {
  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-stone-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-semibold text-stone-900">
            {manifest.summary.total_entities}
          </p>
          <p className="text-xs text-stone-500">Total Entities</p>
        </div>
        <div className="bg-stone-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-semibold text-stone-900">
            {manifest.summary.total_relationships}
          </p>
          <p className="text-xs text-stone-500">Relationships</p>
        </div>
        <div className="bg-stone-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-semibold text-stone-900">
            {manifest.summary.components.length}
          </p>
          <p className="text-xs text-stone-500">Components</p>
        </div>
      </div>

      {/* Category breakdown */}
      <div>
        <h4 className="text-sm font-medium text-stone-700 mb-2">Categories</h4>
        <div className="flex flex-wrap gap-2">
          {Object.entries(manifest.summary.categories).map(([cat, count]) => (
            <span
              key={cat}
              className="text-xs px-2.5 py-1 rounded-full bg-stone-100 text-stone-600"
            >
              {CATEGORY_LABELS[cat] || cat}: {count}
            </span>
          ))}
        </div>
      </div>

      {/* Components with entities */}
      {manifest.components.map((comp) => (
        <div key={comp.name} className="border border-stone-200 rounded-lg overflow-hidden">
          <div className="bg-stone-50 px-3 py-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-stone-800">{comp.name}</h4>
              <span className="text-xs text-stone-400">{comp.entity_count} entities</span>
            </div>
          </div>
          <div>
            {comp.entities.map((entity, i) => (
              <EntityRow key={`${entity.qualified_id}-${i}`} entity={entity} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────
export default function DiagramTabs({ scanId, perspectives, components }: DiagramTabsProps) {
  const [active, setActive] = useState<string>("er");
  const [viewMode, setViewMode] = useState<ViewMode>("graph");
  const [showPublish, setShowPublish] = useState(false);
  const [selectedComponent, setSelectedComponent] = useState<string>("");
  const [showManifest, setShowManifest] = useState(false);
  const [manifestView, setManifestView] = useState<"business" | "json">("business");

  const { data: graphData, isLoading: graphLoading } = useQuery({
    queryKey: ["diagram-data", scanId, active, selectedComponent],
    queryFn: async () => {
      const data = await api.getDiagramData(scanId, active, selectedComponent || undefined);
      console.log(`[DiagramTabs] Fetching: ${active} | Filter: ${selectedComponent}`);
      console.log(`[DiagramTabs] Received nodes:`, data?.nodes?.length);
      return data;
    },
    enabled: viewMode === "graph",
  });

  const { data: mermaidData, isLoading: mermaidLoading } = useQuery({
    queryKey: ["diagram", scanId, active, selectedComponent],
    queryFn: () => api.getDiagram(scanId, active, selectedComponent || undefined),
    enabled: viewMode === "mermaid",
  });

  const { data: manifest } = useQuery({
    queryKey: ["manifest", scanId],
    queryFn: () => api.getManifest(scanId),
    enabled: showManifest,
  });

  const copyCode = () => {
    if (mermaidData?.mermaid_code) {
      navigator.clipboard.writeText(mermaidData.mermaid_code);
    }
  };

  const activeTab = DIAGRAM_TABS.find((t) => t.id === active) || DIAGRAM_TABS[0];

  return (
    <div>
      {/* Tabs + actions */}
      <div className="flex items-center justify-between border-b border-stone-200 mb-4">
        <div className="flex">
          {DIAGRAM_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActive(tab.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                active === tab.id
                  ? "border-stone-900 text-stone-900"
                  : "border-transparent text-stone-400 hover:text-stone-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 pb-1">
          {components && components.length > 1 && (
            <select
              value={selectedComponent}
              onChange={(e) => setSelectedComponent(e.target.value)}
              className="text-xs px-2 py-1 rounded-md border border-stone-200 bg-white text-stone-600 focus:outline-none"
            >
              <option value="">All components</option>
              {components.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          )}
          <button
            onClick={() => setShowManifest(true)}
            className="text-xs px-2.5 py-1 rounded-md bg-stone-50 text-stone-500 border border-stone-200 hover:bg-stone-100"
          >
            Data Manifest
          </button>
          <button
            onClick={() => setShowPublish(true)}
            className="text-xs px-2.5 py-1 rounded-md bg-stone-100 text-stone-600 hover:bg-stone-200"
          >
            Publish as Pattern
          </button>
          <div className="flex items-center gap-1">
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
      </div>

      {/* Graph view */}
      {viewMode === "graph" && (
        <FlowGraph
          nodes={graphData?.nodes || []}
          edges={graphData?.edges || []}
          isLoading={graphLoading}
          height="550px"
          maxNodes={150}
          direction={activeTab.direction}
          showDirectionToggle={true}
          showMiniMap={true}
          emptyMessage={`No entities found for the ${activeTab.label} view.`}
        />
      )}

      {/* Mermaid view */}
      {viewMode === "mermaid" && (
        <div>
          {mermaidLoading && <p className="text-stone-400 text-sm">Loading diagram...</p>}
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

      {/* Manifest modal */}
      {showManifest && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl mx-4 max-h-[85vh] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-stone-200 flex-shrink-0">
              <h2 className="text-lg font-semibold text-stone-900">Data Manifest</h2>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 bg-stone-100 rounded-md p-0.5">
                  <button
                    onClick={() => setManifestView("business")}
                    className={`text-xs px-2.5 py-1 rounded ${
                      manifestView === "business"
                        ? "bg-white text-stone-900 shadow-sm"
                        : "text-stone-500"
                    }`}
                  >
                    Overview
                  </button>
                  <button
                    onClick={() => setManifestView("json")}
                    className={`text-xs px-2.5 py-1 rounded ${
                      manifestView === "json"
                        ? "bg-white text-stone-900 shadow-sm"
                        : "text-stone-500"
                    }`}
                  >
                    JSON
                  </button>
                </div>
                {manifest && (
                  <button
                    onClick={() => {
                      const blob = new Blob(
                        [JSON.stringify(manifest, null, 2)],
                        { type: "application/json" }
                      );
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `manifest-${scanId}.json`;
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                    className="text-xs px-2.5 py-1 rounded-md bg-stone-100 text-stone-600 hover:bg-stone-200"
                  >
                    Download JSON
                  </button>
                )}
                <button
                  onClick={() => setShowManifest(false)}
                  className="text-stone-400 hover:text-stone-600 text-lg leading-none px-1"
                >
                  &times;
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-4">
              {!manifest ? (
                <p className="text-stone-400 text-sm">Loading manifest...</p>
              ) : manifestView === "business" ? (
                <ManifestBusinessView manifest={manifest} />
              ) : (
                <pre className="text-xs font-mono text-stone-700 bg-stone-50 rounded-lg p-4 overflow-auto whitespace-pre">
                  {JSON.stringify(manifest, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Publish modal */}
      {showPublish && (
        <PublishPatternModal
          scanId={scanId}
          perspectives={perspectives || ["er", "dataflow"]}
          activePerspective={active}
          onClose={() => setShowPublish(false)}
          components={components}
        />
      )}
    </div>
  );
}
