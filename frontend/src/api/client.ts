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
}

export interface ScanResponse {
  scan_id: string;
  status: string;
  repo_url: string;
  branch: string;
  created_at: string;
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

export const api = {
  startScan: (req: ScanRequest) =>
    request<ScanResponse>("/scan", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  getScan: (id: string) => request<ScanResponse>(`/scan/${id}`),

  listScans: () => request<ScanResponse[]>("/scan"),

  deleteAllScans: () => request<void>("/scan", { method: "DELETE" }),

  getDiagram: (scanId: string, perspective: string) =>
    request<DiagramResponse>(`/scan/${scanId}/diagrams/${perspective}`),

  getScanEntities: (scanId: string) =>
    request<KnowledgeGraphResponse>(`/scan/${scanId}/entities`),

  getDiagramData: (scanId: string, perspective: string) =>
    request<KnowledgeGraphResponse>(
      `/scan/${scanId}/diagrams/${perspective}/data`
    ),

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

  // Graph / Knowledge Graph
  getGraphStatus: () => request<GraphStatusResponse>("/graph/status"),

  getKnowledgeGraph: (scanId?: string) => {
    const params = scanId ? `?scan_id=${scanId}` : "";
    return request<KnowledgeGraphResponse>(`/graph/knowledge${params}`);
  },

  getConceptHierarchy: () =>
    request<ConceptHierarchyResponse>("/graph/concepts"),

  getRelatedPatterns: (patternId: string) =>
    request<{ results: PatternListItem[]; total: number }>(
      `/graph/patterns/${patternId}/related`
    ),
};
