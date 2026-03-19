import type { AgentRunResult } from "../types/agents";

const BASE_URL = "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface ScanRequest {
  repo_url: string;
  branch: string;
  perspectives?: string[];
}

export interface ScanResponse {
  scan_id: string;
  status: string;
  repo_url: string;
  branch: string;
  created_at: string;
  perspectives: string[];
  components: string[];
}

export interface DiagramResponse {
  scan_id: string;
  perspective: string;
  mermaid_code: string;
  metadata: Record<string, unknown>;
}

export interface TemplateResponse {
  id: string;
  name: string;
  perspective: string;
  template_content: string;
  placeholders: string[];
  created_at: string;
}

export interface TemplateCreateRequest {
  name: string;
  perspective: string;
  template_content: string;
  placeholders: string[];
}

export type PatternStatus = "draft" | "review" | "approved" | "deprecated";

export interface PatternResponse {
  id: string;
  title: string;
  description: string;
  owner: string;
  status: PatternStatus;
  tags: string[];
  content: string;
  mermaid_diagrams: string[];
  created_at: string;
  updated_at: string;
  version: number;
  linked_scan_id: string | null;
}

export interface PatternListItem {
  id: string;
  title: string;
  description: string;
  owner: string;
  status: PatternStatus;
  tags: string[];
  updated_at: string;
  version: number;
}

export interface PatternSearchResponse {
  results: PatternListItem[];
  total: number;
}

export interface PatternCreateRequest {
  title: string;
  description: string;
  owner: string;
  tags: string[];
  content: string;
  linked_scan_id?: string;
}

export interface PublishFromScanRequest {
  title: string;
  description: string;
  owner: string;
  tags?: string[];
  perspectives?: string[];
  content?: string;
  component?: string;
}

export interface ComponentMap {
  [name: string]: { entity_count: number; entity_ids: string[] };
}

export interface PatternUpdateRequest {
  title?: string;
  description?: string;
  owner?: string;
  tags?: string[];
  content?: string;
}

// Graph types
export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface KnowledgeGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: Record<string, unknown>;
}

export interface GraphStatusResponse {
  available: boolean;
  node_count: number;
  edge_count: number;
  details: Record<string, unknown>;
}

export interface ConceptNode {
  id: string;
  label: string;
  broader: string | null;
  narrower: string[];
}

export interface ConceptHierarchyResponse {
  concepts: ConceptNode[];
}

// Data Manifest types
export interface ManifestField {
  name: string;
  type: string;
}

export interface ManifestEntity {
  name: string;
  type: string;
  qualified_id: string;
  location: { file: string; line: number };
  schema?: { fields: ManifestField[] };
  methods?: string[];
  http_method?: string;
  route?: string;
  lineage?: {
    downstream?: { target: string; type: string }[];
    upstream?: { source: string; type: string }[];
  };
}

export interface ManifestComponent {
  name: string;
  entity_count: number;
  entities: ManifestEntity[];
}

export interface DataManifest {
  version: string;
  scan_id: string;
  repository: string;
  branch: string;
  generated_at: string;
  summary: {
    total_entities: number;
    total_relationships: number;
    components: string[];
    categories: Record<string, number>;
    entity_types: Record<string, number>;
  };
  components: ManifestComponent[];
}

export const api = {
  startScan: (req: ScanRequest) =>
    request<ScanResponse>("/scan", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  getScan: (id: string) => request<ScanResponse>(`/scan/${id}`),

  listScans: () => request<ScanResponse[]>("/scan"),

  deleteAllScans: () => request<void>("/scan", { method: "DELETE" }),

  getDiagram: (scanId: string, perspective: string, component?: string) => {
    const params = component ? `?component=${encodeURIComponent(component)}` : "";
    return request<DiagramResponse>(`/scan/${scanId}/diagrams/${perspective}${params}`);
  },

  getScanEntities: (scanId: string) =>
    request<KnowledgeGraphResponse>(`/scan/${scanId}/entities`),

  getDiagramData: (scanId: string, perspective: string, component?: string) => {
    const params = component ? `?component=${encodeURIComponent(component)}` : "";
    return request<KnowledgeGraphResponse>(
      `/scan/${scanId}/diagrams/${perspective}/data${params}`
    );
  },

  getManifest: (scanId: string) =>
    request<DataManifest>(`/scan/${scanId}/manifest`),

  listTemplates: () => request<TemplateResponse[]>("/templates"),

  createTemplate: (req: TemplateCreateRequest) =>
    request<TemplateResponse>("/templates", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  renderTemplate: (id: string, values: Record<string, string>) =>
    request<{ rendered: string }>(`/templates/${id}/render`, {
      method: "POST",
      body: JSON.stringify({ template_id: id, values }),
    }),

  deleteTemplate: (id: string) =>
    request<void>(`/templates/${id}`, { method: "DELETE" }),

  // Pattern Library
  searchPatterns: (params?: {
    query?: string;
    tags?: string[];
    status?: PatternStatus;
    owner?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.query) searchParams.set("query", params.query);
    if (params?.tags) params.tags.forEach((t) => searchParams.append("tags", t));
    if (params?.status) searchParams.set("status", params.status);
    if (params?.owner) searchParams.set("owner", params.owner);
    const qs = searchParams.toString();
    return request<PatternSearchResponse>(`/patterns${qs ? `?${qs}` : ""}`);
  },

  getPattern: (id: string) => request<PatternResponse>(`/patterns/${id}`),

  createPattern: (req: PatternCreateRequest) =>
    request<PatternResponse>("/patterns", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  updatePattern: (id: string, req: PatternUpdateRequest) =>
    request<PatternResponse>(`/patterns/${id}`, {
      method: "PUT",
      body: JSON.stringify(req),
    }),

  deletePattern: (id: string) =>
    request<void>(`/patterns/${id}`, { method: "DELETE" }),

  transitionPattern: (id: string, status: PatternStatus) =>
    request<PatternResponse>(`/patterns/${id}/transition`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  getPatternTemplate: () =>
    request<{ content: string }>("/patterns/template"),

  createPatternFromScan: (scanId: string, req: PatternCreateRequest) =>
    request<PatternResponse>(`/patterns/from-scan/${scanId}`, {
      method: "POST",
      body: JSON.stringify(req),
    }),

  publishPatternFromScan: (scanId: string, req: PublishFromScanRequest) =>
    request<PatternResponse>(`/patterns/from-scan/${scanId}`, {
      method: "POST",
      body: JSON.stringify(req),
    }),

  getScanComponents: (scanId: string) =>
    request<ComponentMap>(`/scan/${scanId}/components`),

  // Graph / Knowledge Graph
  getGraphStatus: () => request<GraphStatusResponse>("/graph/status"),

  getKnowledgeGraph: (scanId: string) =>
    request<KnowledgeGraphResponse>(`/graph/knowledge?scan_id=${scanId}`),

  getConceptHierarchy: () =>
    request<ConceptHierarchyResponse>("/graph/concepts"),

  getRelatedPatterns: (patternId: string) =>
    request<{ results: PatternListItem[]; total: number }>(
      `/graph/patterns/${patternId}/related`
    ),

  // Agent Analysis
  triggerAgentAnalysis: (scanId: string) =>
    request<AgentRunResult>(`/agents/analyze/${scanId}`, { method: "POST" }),

  getAgentInsights: (scanId: string) =>
    request<AgentRunResult>(`/agents/insights/${scanId}`),

  getAgentInsightsByCategory: (scanId: string, category: string) =>
    request<AgentRunResult>(`/agents/insights/${scanId}/${category}`),
};
