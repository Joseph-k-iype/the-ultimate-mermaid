# PatternViz Developer Guide

Technical reference for developers extending, deploying, or contributing to PatternViz.

---

## Architecture Overview

```
frontend/ (React + TypeScript + Vite)
  src/
    api/client.ts        ← Single API client, all types
    pages/               ← Route-level components
    components/          ← Reusable UI components

backend/ (FastAPI + Python 3.11+)
  app/
    main.py              ← FastAPI app, lifespan, CORS, routers
    config.py            ← pydantic-settings, reads .env
    analyzers/           ← Code analysis (AST + regex)
    generators/          ← Mermaid diagram generation
    graph/               ← FalkorDB + SKOS ontology
    models/              ← Pydantic data models
    routes/              ← API endpoints
    services/            ← Business logic orchestration
    utils/               ← Deterministic ID generation
```

### Request Flow

```
HTTP Request
  → FastAPI Router (routes/)
    → Service Layer (services/)
      → Analyzers + Generators (analyzers/, generators/)
      → Graph Service (graph/)
    ← Response Model (models/)
  ← JSON Response
```

---

## Configuration

All settings are managed via `pydantic-settings` with the `PATTERNVIZ_` prefix.

### Sources (priority order)
1. Environment variables (highest)
2. `backend/.env` file
3. Defaults in `config.py` (lowest)

### Settings Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PATTERNVIZ_HOST` | `0.0.0.0` | Server bind address |
| `PATTERNVIZ_PORT` | `8000` | Server port |
| `PATTERNVIZ_CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins (JSON array) |
| `PATTERNVIZ_CLONE_DIR` | OS temp + `/patternviz` | Temp directory for cloned repos (cross-platform) |
| `PATTERNVIZ_HTTP_PROXY` | _(empty)_ | HTTP proxy for git operations |
| `PATTERNVIZ_HTTPS_PROXY` | _(empty)_ | HTTPS proxy for git operations |
| `PATTERNVIZ_NO_PROXY` | `localhost,127.0.0.1` | Proxy bypass list |
| `PATTERNVIZ_USE_SYSTEM_SSL` | `true` | Auto-detect OS certificate store |
| `PATTERNVIZ_SSL_CA_FILE` | _(empty)_ | Explicit path to a PEM CA bundle file |
| `PATTERNVIZ_SSL_CA_PATH` | _(empty)_ | Explicit path to a directory of CA certificates |
| `PATTERNVIZ_FALKORDB_ENABLED` | `true` | Enable FalkorDB graph database |
| `PATTERNVIZ_FALKORDB_HOST` | `localhost` | FalkorDB host |
| `PATTERNVIZ_FALKORDB_PORT` | `6379` | FalkorDB port |
| `PATTERNVIZ_FALKORDB_GRAPH` | `patternviz` | FalkorDB graph name |

### Cross-Platform Defaults

- **CLONE_DIR:** Uses `tempfile.gettempdir()` — resolves to `/tmp/patternviz` on Linux/macOS, `C:\Users\...\AppData\Local\Temp\patternviz` on Windows

### Enterprise Proxy & SSL

When `PATTERNVIZ_HTTPS_PROXY` is set, the `RepoService` passes proxy environment variables to Git's subprocess. When `PATTERNVIZ_USE_SYSTEM_SSL` is true (default), Git uses the system CA bundle.

**CA bundle resolution priority (`_find_ca_bundle()`):**

1. **User-specified** `SSL_CA_FILE` — if set and file exists, used immediately
2. **Platform-specific paths:**
   - **Windows:** Git for Windows bundles (Program Files, Scoop, Chocolatey install paths)
   - **macOS:** `/etc/ssl/cert.pem`, Homebrew OpenSSL (Intel + Apple Silicon)
   - **Linux:** Debian, RHEL/CentOS, openSUSE, Alpine CA paths
3. **Python `ssl.get_default_verify_paths()`** — OpenSSL's configured paths
4. **Windows certificate store export** — PowerShell extracts all trusted root CAs from `Cert:\LocalMachine\Root` to a temporary PEM file
5. **Python `certifi` bundle** — always available as last resort

**CA directory resolution (`_find_ca_path()`):**
1. User-specified `SSL_CA_PATH`
2. Platform defaults (`/etc/ssl/certs`, Git for Windows certs dir)

The resolved paths are set as `GIT_SSL_CAINFO`, `GIT_SSL_CAPATH`, `SSL_CERT_FILE`, `SSL_CERT_DIR`, and `REQUESTS_CA_BUNDLE` in the git subprocess environment. This avoids `GIT_SSL_NO_VERIFY=true`.

---

## Backend

### Dependencies

```
fastapi         — Web framework
uvicorn         — ASGI server
pydantic        — Data validation
pydantic-settings — Environment config
gitpython       — Git operations
jinja2          — Template rendering
httpx           — HTTP client
falkordb        — Graph database client (optional at runtime)
certifi         — SSL certificate bundle
```

### Running

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### Testing

```bash
cd backend
python -m pytest tests/ -v
```

Tests run without FalkorDB. The graph service gracefully returns empty/None when unavailable, and the graph API endpoint tests isolate scan state to avoid interference.

### Adding a New Code Analyzer

1. Create `backend/app/analyzers/my_language.py`
2. Subclass `CodeAnalyzer` from `analyzers/base.py`
3. Implement `supported_extensions` and `analyze(file_path, content) -> (entities, relationships)`
4. Register in `analyzers/registry.py`:
   ```python
   default_registry.register(MyLanguageAnalyzer())
   ```

### Adding a New Perspective

1. Define the perspective in `graph/ontology.py` → `PERSPECTIVE_DEFINITIONS`
2. Create a perspective analyzer in `analyzers/` subclassing `PerspectiveAnalyzer`
3. Create a Mermaid generator in `generators/` subclassing `MermaidGenerator`
4. Wire into `services/scan_orchestrator.py`:
   - Add to `PERSPECTIVES` tuple
   - Add to `_PERSPECTIVE_ANALYZERS` and `_MERMAID_GENERATORS` dicts

### Mermaid Generation

All generators extend `MermaidGenerator` which provides:

- `sanitize_id(raw_id)` — Makes IDs Mermaid-safe (handles digits, keywords, special chars)
- `sanitize_label(label)` — Escapes `"()[]{}` using Mermaid HTML entities
- `truncate_entities(entities, rels, max=80)` — Keeps the most-connected entities

The `MAX_ENTITIES = 80` limit prevents browser rendering failures with large diagrams.

### Graph Service

`GraphService` is a singleton at `graph/graph_service.py`. It wraps all FalkorDB operations:

- **Connection:** Lazy connect in `main.py` lifespan. Falls back silently.
- **Schema:** Indexes on CodeEntity, Scan, Pattern, Concept nodes. SKOS Concept hierarchy with BROADER/NARROWER edges.
- **Cypher queries:** All go through `_query()` which catches exceptions and returns None.
- **Perspective queries:** Use `PerspectiveDefinition` from `ontology.py` to build Cypher dynamically.

### SKOS Ontology

Defined in `graph/ontology.py`:

```
CodeConstruct → class, function, method, variable
APIElement    → endpoint, model
DataAccessor  → db_read, db_write, file_reader, file_writer
MessageHandler → consumer, producer
```

`PerspectiveDefinition` replaces hard-coded filtering in perspective analyzers. Each definition declares which `entity_types` and `relationship_types` it selects.

---

## Frontend

### Stack

```
React 18       — UI framework
TypeScript     — Type safety
Vite           — Build tool + dev server
TanStack Query — Server state management
React Router   — Client-side routing
@xyflow/react  — Interactive graph visualization (React Flow v12)
elkjs          — ELK hierarchical layout algorithm
Mermaid        — Diagram rendering
Tailwind CSS   — Utility-first styling
```

### Running

```bash
cd frontend
npm install
npm run dev        # Dev server on :5173
npm run build      # Production build
npx tsc --noEmit   # Type check
```

### Project Structure

```
src/
├── api/client.ts          — Typed API client, all interfaces
├── App.tsx                — Router + nav + providers
├── pages/
│   ├── Dashboard.tsx      — Scan form + history
│   ├── DiagramPage.tsx    — Perspective diagram viewer
│   ├── KnowledgeGraphPage.tsx — Full-page graph visualization
│   ├── PatternLibraryPage.tsx — Pattern search + grid
│   ├── PatternDetailPage.tsx  — Pattern view + transitions
│   └── PatternEditorPage.tsx  — Markdown editor + preview
└── components/
    ├── FlowGraph.tsx      — Reusable React Flow + ELK layout component
    ├── MermaidRenderer.tsx — Self-healing Mermaid rendering
    ├── DiagramTabs.tsx    — Perspective tabs with Graph/Mermaid toggle
    ├── ScanForm.tsx       — Repository URL input
    ├── PatternCard.tsx    — Pattern grid item
    ├── StatusBadge.tsx    — Status pill
    ├── MarkdownRenderer.tsx — Markdown + Mermaid blocks
    ├── TemplateEditor.tsx — Template creation form
    └── PlaceholderForm.tsx — Template rendering form
```

### API Client

`api/client.ts` exports a single `api` object with typed methods for every endpoint. All requests go through a generic `request<T>()` wrapper that handles errors and JSON parsing.

### Adding a New Page

1. Create `src/pages/MyPage.tsx`
2. Add route in `App.tsx`: `<Route path="/my-page" element={<MyPage />} />`
3. Add nav link in `App.tsx`

### MermaidRenderer Self-Healing

The component tries four rendering strategies in sequence:

1. Raw code → `mermaid.render()`
2. Sanitized code (fix quotes, prefix numeric IDs)
3. Simplified code (strip complex node shapes)
4. Truncated code (first 60 lines, preserving subgraph structure)

A yellow notice appears when auto-correction was applied.

### FlowGraph Component

`FlowGraph.tsx` is the shared React Flow + ELK layout component used by both `DiagramTabs` (perspective views) and `KnowledgeGraphPage`. It accepts:

| Prop | Type | Description |
|------|------|-------------|
| `nodes` | `GraphNode[]` | API graph nodes to render |
| `edges` | `GraphEdge[]` | API graph edges to render |
| `isLoading` | `boolean` | Show loading spinner |
| `height` | `string` | Container height (e.g., `"500px"` or `"100%"`) |
| `maxNodes` | `number` | Cap nodes for performance (default: 200) |
| `direction` | `"RIGHT" \| "DOWN"` | ELK layout direction |
| `showDirectionToggle` | `boolean` | Show horizontal/vertical buttons |
| `showMiniMap` | `boolean` | Show navigation minimap |
| `emptyMessage` | `string` | Text when no nodes to display |

Features:
- **ELK layout** (`elkjs`) with compound hierarchy — entities grouped by ontology category
- **Custom `EntityNode`** component with type icon, color, and tooltip
- **Horizontal/Vertical toggle** for layout direction
- **Interactive legend** for type filtering
- **MiniMap** for navigation on large graphs
- Loading spinner during layout computation
- Grid fallback if ELK fails

### DiagramTabs — Graph/Mermaid Toggle

`DiagramTabs` now offers two view modes toggled via **Graph** / **Mermaid** buttons:
- **Graph:** Uses `FlowGraph` with data from `GET /api/scan/{id}/diagrams/{perspective}/data`
- **Mermaid:** Uses `MermaidRenderer` with Mermaid code from `GET /api/scan/{id}/diagrams/{perspective}`

Each perspective has a default layout direction (ingestion/output = vertical, er/transformation = horizontal).

---

## API Reference

### Scan Endpoints

#### `POST /api/scan`
Start a repository scan.
```json
{ "repo_url": "https://github.com/user/repo", "branch": "main" }
```
Response: `ScanResponse` with `scan_id`, `status`, `repo_url`, `branch`, `created_at`.

#### `GET /api/scan`
List all scans. Returns `ScanResponse[]`.

#### `DELETE /api/scan`
Clear all scans and graph data. Returns 204.

#### `GET /api/scan/{scan_id}`
Get scan status. Returns `ScanResponse`.

#### `GET /api/scan/{scan_id}/entities`
Get raw entities and relationships. Returns `{ nodes: GraphNode[], edges: GraphEdge[] }`.

#### `GET /api/scan/{scan_id}/diagrams/{perspective}/data`
Get perspective-filtered entities and relationships as graph data (for React Flow).
Returns `{ nodes: GraphNode[], edges: GraphEdge[] }`.

#### `GET /api/scan/{scan_id}/diagrams/{perspective}`
Get Mermaid diagram. Perspective must be: `ingestion`, `er`, `transformation`, `output`.
Returns `DiagramResponse` with `mermaid_code` and `metadata`.

### Pattern Endpoints

#### `POST /api/patterns`
Create a pattern.
```json
{
  "title": "Auth Pattern",
  "description": "JWT authentication",
  "owner": "platform-team",
  "tags": ["auth", "security"],
  "content": "# Auth\n\n```mermaid\ngraph TD\n    A-->B\n```"
}
```

#### `GET /api/patterns`
Search patterns. Query params: `query`, `tags`, `status`, `owner`.

#### `GET /api/patterns/{id}` | `PUT` | `DELETE`
Pattern CRUD.

#### `POST /api/patterns/{id}/transition`
Change status. Body: `{ "status": "review" }`.

#### `GET /api/patterns/template`
Get the system design template.

### Graph Endpoints

#### `GET /api/graph/status`
FalkorDB connection status and node/edge counts.

#### `GET /api/graph/knowledge?scan_id=`
Knowledge graph nodes and edges. Falls back to in-memory scans when FalkorDB is offline.

#### `GET /api/graph/concepts`
SKOS concept hierarchy tree.

#### `GET /api/graph/patterns/{id}/related`
Find patterns related by shared tags.

#### `GET /api/graph/stats`
Node and edge count breakdown by label/type.

---

## Design Decisions

### Why In-Memory Storage?

Scans and patterns are stored in Python dicts, not a SQL database. This keeps the project simple and dependency-free. FalkorDB adds persistence and graph queries when available but is not required.

### Why FalkorDB?

FalkorDB is a Redis-compatible graph database that supports Cypher queries. It was chosen because:
- Single binary, runs as a Docker container
- Redis-compatible protocol (no new ports to open)
- Cypher query language for graph traversal
- Fast enough for code analysis graphs (thousands of nodes)

### Why ELK Layout?

ELK (Eclipse Layout Kernel) provides hierarchical layout with:
- Compound nodes (groups within groups)
- Cross-group edge routing
- Layer sweep crossing minimization
- Better handling of large graphs than dagre

### Why SKOS?

W3C SKOS (Simple Knowledge Organization System) provides a standard vocabulary for concept hierarchies. Using BROADER/NARROWER relationships lets tag searches find semantically related patterns without exact matches.

### Why Mermaid?

Mermaid is the most widely supported diagram-as-code format. It renders in GitHub, Notion, Confluence, VS Code, and dozens of other tools. Generated diagrams are portable.

---

## Deployment

### Docker Compose (Recommended)

```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: ./backend/.env
    depends_on:
      - falkordb

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"

  falkordb:
    image: falkordb/falkordb
    ports:
      - "6379:6379"
```

### Production Notes

- Set `PATTERNVIZ_CORS_ORIGINS` to your frontend domain
- Use a reverse proxy (nginx/Caddy) in front of both services
- FalkorDB data is ephemeral by default; mount a volume for persistence:
  ```yaml
  falkordb:
    volumes:
      - falkordb_data:/data
  ```
- The clone directory (`/tmp/patternviz`) is cleaned up on shutdown; in production, consider a persistent volume if you want cached clones

---

## Troubleshooting

### Scan fails with SSL error
Set `PATTERNVIZ_USE_SYSTEM_SSL=true` and ensure your system CA store includes your corporate root CA. If auto-detection fails, specify the path explicitly:
```env
PATTERNVIZ_SSL_CA_FILE=/path/to/ca-bundle.pem          # Linux/macOS
PATTERNVIZ_SSL_CA_FILE=C:\certs\corporate-ca-bundle.pem # Windows
```

### Scan fails with SSL on Windows
Ensure Git for Windows is installed (provides CA bundles). If not available, PatternViz will export certificates from the Windows certificate store automatically. You can also point to a specific bundle:
```env
PATTERNVIZ_SSL_CA_FILE=C:\Program Files\Git\mingw64\etc\ssl\certs\ca-bundle.crt
```

### Scan fails with proxy error
Verify `PATTERNVIZ_HTTPS_PROXY` is set correctly. Test with:
```bash
# Linux/macOS
HTTPS_PROXY=http://proxy:8080 git clone https://github.com/user/repo /tmp/test

# Windows (PowerShell)
$env:HTTPS_PROXY="http://proxy:8080"; git clone https://github.com/user/repo C:\Temp\test
```

### Mermaid diagram shows "auto-corrected" notice
The diagram was too complex for the browser renderer. The backend limits to 80 entities and the frontend truncates to 60 lines. This is expected for large codebases.

### Knowledge graph shows "No graph data"
Either no scans have been run, or FalkorDB is offline and no in-memory scans exist. Run a scan first.

### FalkorDB won't connect
Ensure the container is running: `docker ps | grep falkordb`. Check that port 6379 is not used by Redis.

### Tests fail with import errors
Run `pip install -e ".[dev]"` from the `backend/` directory to install all dependencies including test dependencies.
