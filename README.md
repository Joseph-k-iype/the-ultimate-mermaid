# PatternViz

> Scan any Git repository. Extract architectural patterns. Visualize them instantly.

PatternViz is a code pattern visualization platform that analyzes repository source code using AST parsing, maps entities and relationships into a knowledge graph, and renders interactive architectural diagrams across four distinct perspectives — all from a single scan.

---

## Table of Contents

- [Why PatternViz](#why-patternviz)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Scanning a Repository](#scanning-a-repository)
- [Architectural Perspectives](#architectural-perspectives)
- [Knowledge Graph](#knowledge-graph)
- [Pattern Library](#pattern-library)
- [Mermaid Templates](#mermaid-templates)
- [Enterprise Proxy Setup](#enterprise-proxy-setup)
- [Configuration Reference](#configuration-reference)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)

---

## Why PatternViz

Understanding a codebase is hard. Reading thousands of files to find how data flows, which classes relate to each other, or where database writes happen takes hours. PatternViz automates this:

- **One scan, four views** — See ingestion, entity relationships, data transformations, and output flows without reading a single file
- **Interactive knowledge graph** — Explore entities and relationships visually with zoom, pan, filtering, and layout controls
- **Pattern catalog** — Document and share architectural patterns with your team using Markdown and embedded Mermaid diagrams
- **No lock-in** — All diagrams use standard Mermaid syntax, portable to GitHub, Notion, Confluence, and dozens of other tools
- **Enterprise ready** — Works behind corporate proxies with TLS inspection, uses system SSL certificates

---

## Key Features

### Repository Scanning
Point PatternViz at any Git repository URL and it extracts a complete entity graph:

**12 entity types detected:**

| Category | Entity Types |
|----------|-------------|
| Code Constructs | `class`, `function`, `method`, `variable` |
| API Elements | `endpoint` (Flask/FastAPI routes), `model` |
| Data Accessors | `db_read`, `db_write`, `file_reader`, `file_writer` |
| Message Handlers | `consumer`, `producer` |

**9 relationship types mapped:**
`calls`, `inherits`, `imports`, `uses`, `contains`, `produces`, `consumes`, `reads`, `writes`

### Four Architectural Perspectives
Every scan generates four Mermaid diagrams, each filtering the entity graph through a different lens:

| Perspective | Shows | Diagram Type |
|-------------|-------|--------------|
| **Ingestion** | API endpoints, message consumers, file readers | Flowchart TD |
| **Entity-Relationship** | Classes, models, inheritance, associations | ER Diagram |
| **Transformation** | Functions, DB operations, file I/O pipelines | Flowchart LR |
| **Output** | Database writes, file writers, message producers | Flowchart TD |

### Interactive Knowledge Graph
Full-canvas graph visualization powered by React Flow and ELK layout:
- Color-coded nodes by entity type (12 distinct colors)
- Grouped by SKOS ontology categories (CodeConstruct, APIElement, DataAccessor, MessageHandler)
- Horizontal or vertical layout toggle
- Search, filter by type, filter by scan
- Zoom, pan, drag nodes, minimap navigation
- Handles graphs with 500+ nodes

### Pattern Library
A collaborative catalog for architectural patterns and system designs:
- **Markdown + Mermaid editor** with live split-pane preview
- **Status workflow:** Draft → Review → Approved → Deprecated (enforced transitions)
- **Search** by text, tags, status, or owner
- **SKOS concept traversal** for semantic tag matching (when FalkorDB is connected)
- **Related patterns** discovery via shared tags and linked scans
- **System design template** pre-filled for new patterns with sections for architecture, data flow, components, decisions, and trade-offs

### Self-Healing Diagrams
Large codebases can produce diagrams too complex for browser rendering. PatternViz handles this automatically:

1. **Backend:** Limits to 80 most-connected entities per diagram, escapes all special characters
2. **Frontend:** 4-level retry — raw → sanitized → simplified → truncated (preserving subgraph structure)
3. A notice appears when auto-correction was applied; raw code is always accessible

### Mermaid Templates
Create reusable diagram templates with `{{ placeholder }}` variables. Select a saved template, fill in the values, and render a customized Mermaid diagram instantly.

### FalkorDB Knowledge Graph (Optional)
When FalkorDB is running, PatternViz stores everything in a persistent graph database:
- SKOS concept hierarchy with BROADER/NARROWER edges for semantic search
- Cypher-powered perspective queries replacing in-memory filtering
- Pattern search with concept traversal (find patterns tagged with related concepts)
- Related pattern discovery across shared tags and scans
- Falls back to in-memory mode automatically when unavailable

---

## Quick Start

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| Git | Any | For cloning scanned repos |
| Docker | _(optional)_ | For FalkorDB graph database |

### 1. Start the Backend

```bash
cd backend
pip install -e ".[dev]"
cp ../.env.example .env          # Edit proxy/FalkorDB settings if needed
uvicorn app.main:app --reload
```

The API starts at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 2. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### 3. Optional: Start FalkorDB

```bash
docker run -d --name falkordb -p 6379:6379 falkordb/falkordb
```

PatternViz detects FalkorDB on startup and enables graph persistence automatically. Everything works without it — the app falls back to in-memory storage.

### 4. Scan Your First Repository

1. Open `http://localhost:5173`
2. Enter a Git repository URL (e.g., `https://github.com/tiangolo/fastapi`)
3. Click **Scan Repository**
4. Explore the four architectural diagrams
5. Navigate to **Knowledge Graph** to see the interactive entity graph

---

## How It Works

```
Repository URL
     |
     v
[1. Clone] ── Shallow clone (depth=1), proxy/SSL-aware
     |
     v
[2. Analyze] ── Walk files → Python AST parser + regex fallback
     |              Extracts entities (classes, endpoints, db ops...)
     |              Maps relationships (calls, inherits, reads...)
     v
[3. Filter] ── Four perspective analyzers slice the entity graph:
     |           Ingestion | ER | Transformation | Output
     v
[4. Generate] ── Mermaid generators produce diagram code
     |              with sanitized IDs, escaped labels, entity limits
     v
[5. Store] ── In-memory dict (always)
     |         + FalkorDB graph (when available)
     v
[6. Serve] ── FastAPI endpoints return Mermaid code + graph data
     |
     v
[7. Render] ── React frontend with self-healing Mermaid
               + React Flow knowledge graph with ELK layout
```

### What Gets Analyzed

The Python AST analyzer extracts:
- **Class definitions** — name, attributes, methods, decorators
- **Function/method signatures** — parameters, return annotations
- **HTTP endpoints** — Flask/FastAPI route decorators with method and path
- **Database operations** — Calls to `.query()`, `.filter()`, `.commit()`, `.execute()`
- **File I/O** — `open()`, `.read()`, `.write()` calls
- **HTTP clients** — `requests.*`, `httpx.*` calls
- **Messaging** — `produce`, `consume`, `publish`, `subscribe` patterns
- **Inheritance** — Base class relationships
- **Import relationships** — Module dependencies

All entity IDs are deterministic (same code produces same IDs), so re-scanning updates rather than duplicates.

---

## Scanning a Repository

### From the Dashboard

1. Navigate to the **Dashboard** (home page)
2. Enter the Git repository URL
3. Optionally change the branch (defaults to `main`)
4. Click **Scan Repository**
5. When complete, you are redirected to the diagram viewer

### From the API

```bash
curl -X POST http://localhost:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo", "branch": "main"}'
```

### What Happens During a Scan

1. Repository is shallow-cloned (depth=1) to a temporary directory
2. Proxy and SSL settings are applied to the git process if configured
3. All files are walked, skipping `node_modules`, `__pycache__`, `.venv`, etc.
4. Python files get full AST analysis; other files use regex patterns
5. Entities and relationships are extracted and deduplicated
6. Four perspective analyzers filter the graph into focused views
7. Mermaid generators produce diagram code (max 80 entities per diagram)
8. If FalkorDB is connected, all data is stored in the graph database
9. The temporary clone is cleaned up

### Managing Scans

- **List scans:** `GET /api/scan`
- **Clear all scans:** `DELETE /api/scan` (also clears FalkorDB graph data)
- **Get scan entities:** `GET /api/scan/{id}/entities` (raw entity + relationship data)

---

## Architectural Perspectives

### Ingestion — How Data Enters

Shows API endpoints, message consumers, and file readers as entry points with their downstream call chains.

**Entity types included:** `endpoint`, `consumer`, `file_reader`
**Relationship types:** `calls`, `uses`, `reads`, `consumes`

### Entity-Relationship — Structural View

Shows classes and models with their inheritance hierarchies, containment, and associations. Uses Mermaid ER diagram syntax with attribute and method listings.

**Entity types included:** `class`, `model`
**Relationship types:** `inherits`, `contains`, `uses`

### Transformation — Processing Pipeline

Shows the data processing layer between ingestion and output. Functions, database reads/writes, and file operations that transform data.

**Entity types included:** `consumer`, `file_reader`, `db_read`, `producer`, `file_writer`, `db_write`, `function`
**Relationship types:** `calls`, `uses`, `produces`, `consumes`, `reads`, `writes`

### Output — Where Data Goes

Shows data sinks grouped by type: database writes, file writers, and message producers.

**Entity types included:** `producer`, `file_writer`, `db_write`
**Relationship types:** `calls`, `uses`, `writes`, `produces`

### Using Diagrams

- Click the **tab** for each perspective on the diagram page
- Click **Copy Mermaid Code** to copy the diagram source
- Paste into GitHub, Notion, Confluence, VS Code, or any Mermaid-compatible tool

---

## Knowledge Graph

Navigate to **Knowledge Graph** in the top nav bar.

### Graph Controls

| Control | Action |
|---------|--------|
| **Search box** | Filter nodes by name |
| **Scan dropdown** | View entities from one scan or all scans |
| **Horizontal / Vertical** | Toggle ELK layout direction |
| **Legend buttons** | Click entity types to show/hide them |
| **Scroll wheel** | Zoom in/out |
| **Click + drag background** | Pan the canvas |
| **Click + drag node** | Reposition a node |
| **Minimap** (bottom-right) | Click to navigate, drag to pan |
| **+/- buttons** (bottom-left) | Zoom controls |
| **Fit button** | Reset view to fit all nodes |

### Node Color Legend

| Entity Type | Color | Icon |
|-------------|-------|------|
| `class` | Purple | C |
| `function` | Green | f |
| `method` | Light green | m |
| `variable` | Yellow | v |
| `endpoint` | Blue | E |
| `model` | Pink | M |
| `db_read` | Cyan | &#9655; |
| `db_write` | Red | &#9665; |
| `file_reader` | Green | &#8592; |
| `file_writer` | Pink | &#8594; |
| `consumer` | Orange | > |
| `producer` | Rose | < |

### Edge Types

| Type | Style | Meaning |
|------|-------|---------|
| `calls` | Animated | Function/method invocation |
| `inherits` | Solid | Class inheritance |
| `contains` | Solid | Containment (class has method) |
| `uses` | Solid | Usage reference |
| `reads` / `writes` | Solid | Data I/O |
| `produces` / `consumes` | Solid | Message passing |

### Ontology Grouping

Nodes are automatically grouped by their SKOS concept category:

- **CodeConstruct** — class, function, method, variable
- **APIElement** — endpoint, model
- **DataAccessor** — db_read, db_write, file_reader, file_writer
- **MessageHandler** — consumer, producer

---

## Pattern Library

Navigate to **Pattern Library** in the top nav bar.

### Creating a Pattern

1. Click **New Pattern**
2. Fill in: **Title**, **Description**, **Owner**, **Tags** (comma-separated)
3. Write content using Markdown in the left editor pane
4. Embed Mermaid diagrams inside ` ```mermaid ` code fences
5. The right pane shows a live preview with rendered Mermaid
6. Click **Save**

New patterns start pre-filled with a system design template containing sections for:
Overview, Context & Problem Statement, Solution Architecture, Components, Data Flow, API Contracts, Decision Log, Trade-offs, and References.

### Searching and Filtering

| Filter | Description |
|--------|-------------|
| **Search** | Text search across title, description, and content |
| **Status** | Draft, Review, Approved, or Deprecated |
| **Owner** | Team or author name |
| **Tags** | Comma-separated; with FalkorDB, includes SKOS concept matches |

### Pattern Status Workflow

```
Draft ──> Review ──> Approved ──> Deprecated
  ^         |                         |
  |         v                         |
  └─────────┘                         |
  ^                                   |
  └───────────────────────────────────┘
```

Transitions are enforced — you cannot skip steps (e.g., Draft directly to Approved).

### Related Patterns

When FalkorDB is connected, each pattern detail page shows a **Related Patterns** section at the bottom, linking to patterns that:
- Share the same tags (via SKOS concept graph traversal)
- Are linked to the same scan
- Reference the same code entities

---

## Mermaid Templates

Navigate to **Templates** in the top nav bar.

### Creating a Template

1. Enter a **Template name**
2. Select a **Perspective** (ingestion, er, transformation, output)
3. Write Mermaid code with `{{ placeholder }}` variables
4. Click **Save Template**

### Rendering

1. Click a template name from the saved list
2. Fill in the placeholder values
3. Click **Render**
4. The completed diagram renders below

### Example

```
graph TD
    {{ service }}["{{ service_label }}"]
    {{ service }} --> DB["{{ database }}"]
    {{ service }} --> Cache["{{ cache }}"]
    DB --> Analytics["{{ analytics_service }}"]
```

Fill in `service=OrderSvc`, `service_label=Order Service`, `database=PostgreSQL`, `cache=Redis`, `analytics_service=Snowflake` — and get a rendered architecture diagram.

---

## Enterprise Proxy Setup

PatternViz supports enterprise networks where outbound connections require an HTTP/HTTPS proxy, including proxies that perform TLS inspection with custom root CAs.

### Configuration

Edit `backend/.env`:

```env
# Proxy server
PATTERNVIZ_HTTPS_PROXY=http://proxy.corp.example.com:8080
PATTERNVIZ_HTTP_PROXY=http://proxy.corp.example.com:8080
PATTERNVIZ_NO_PROXY=localhost,127.0.0.1

# Use OS certificate store (handles TLS-inspecting proxies)
PATTERNVIZ_USE_SYSTEM_SSL=true
```

### How It Works

When a scan starts, the `RepoService` builds a git environment with:

1. **Proxy variables** — `HTTPS_PROXY`, `HTTP_PROXY`, `NO_PROXY` passed to the git subprocess
2. **SSL CA bundle** — System certificate store is detected automatically:
   - `/etc/ssl/cert.pem` (macOS)
   - `/etc/ssl/certs/ca-certificates.crt` (Debian/Ubuntu)
   - `/etc/pki/tls/certs/ca-bundle.crt` (RHEL/CentOS)
   - Falls back to Python's `certifi` bundle

This avoids `GIT_SSL_NO_VERIFY=true` — your connections remain verified against the proper CA chain.

### Proxy Authentication

For proxies requiring credentials:

```env
PATTERNVIZ_HTTPS_PROXY=http://username:password@proxy.corp.example.com:8080
```

### SOCKS Proxy

```env
PATTERNVIZ_HTTPS_PROXY=socks5://proxy.corp.example.com:1080
```

---

## Configuration Reference

All settings use the `PATTERNVIZ_` prefix. Set via environment variables or `backend/.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `PATTERNVIZ_HOST` | `0.0.0.0` | Server bind address |
| `PATTERNVIZ_PORT` | `8000` | Server port |
| `PATTERNVIZ_CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins (JSON array) |
| `PATTERNVIZ_CLONE_DIR` | `/tmp/patternviz` | Temporary directory for cloned repos |
| `PATTERNVIZ_HTTP_PROXY` | _(empty)_ | HTTP proxy for git operations |
| `PATTERNVIZ_HTTPS_PROXY` | _(empty)_ | HTTPS proxy for git operations |
| `PATTERNVIZ_NO_PROXY` | `localhost,127.0.0.1` | Proxy bypass list |
| `PATTERNVIZ_USE_SYSTEM_SSL` | `true` | Use OS certificate store for git |
| `PATTERNVIZ_FALKORDB_ENABLED` | `true` | Enable FalkorDB graph database |
| `PATTERNVIZ_FALKORDB_HOST` | `localhost` | FalkorDB host |
| `PATTERNVIZ_FALKORDB_PORT` | `6379` | FalkorDB port |
| `PATTERNVIZ_FALKORDB_GRAPH` | `patternviz` | FalkorDB graph name |

**Priority order:** Environment variables > `backend/.env` file > defaults in `config.py`.

See [`.env.example`](.env.example) for a ready-to-copy template.

---

## Project Structure

```
patterns/
  README.md                    This file
  .env.example                 Configuration template
  .gitignore                   Git ignore rules
  docs/
    FEATURES.md                Detailed feature descriptions
    USER_GUIDE.md              Step-by-step usage walkthrough
    DEVELOPER_GUIDE.md         Architecture, extending, deployment

  backend/
    .env                       Local configuration (not committed)
    pyproject.toml             Python dependencies
    app/
      main.py                  FastAPI application entry point
      config.py                Settings (pydantic-settings)
      analyzers/               Code analysis
        base.py                  Abstract base classes
        registry.py              Analyzer registry (maps extensions)
        python_ast.py            Full Python AST analyzer
        generic_regex.py         Regex fallback for other languages
        er_analyzer.py           ER perspective filter
        ingestion_analyzer.py    Ingestion perspective filter
        transformation_analyzer.py  Transformation perspective filter
        output_analyzer.py       Output perspective filter
      generators/              Mermaid diagram generation
        base.py                  Sanitization + truncation helpers
        er_generator.py          ER diagram syntax
        ingestion_generator.py   Flowchart TD syntax
        transformation_generator.py  Flowchart LR syntax
        output_generator.py      Flowchart TD with subgraphs
      graph/                   Knowledge graph
        __init__.py              graph_service singleton export
        ontology.py              SKOS hierarchy + perspective definitions
        graph_service.py         FalkorDB operations + fallback
      models/                  Pydantic models
        domain.py                CodeEntity, Relationship, DiagramData
        graph.py                 GraphNode, GraphEdge, KnowledgeGraphResponse
        pattern.py               PatternModel, status workflow
        requests.py              API request models
        responses.py             API response models
      routes/                  API endpoints
        scan.py                  Scan CRUD + diagram retrieval
        pattern.py               Pattern CRUD + status transitions
        template.py              Template CRUD + rendering
        graph.py                 Knowledge graph + concept hierarchy
      services/                Business logic
        scan_orchestrator.py     Clone → analyze → generate pipeline
        pattern_service.py       Pattern store + graph dual-write
        template_service.py      Jinja2 template rendering
        repo_service.py          Git clone with proxy/SSL support
      utils/
        determinism.py           Deterministic ID generation
    tests/                     95 tests
      conftest.py                Shared fixtures
      test_analyzers.py          AST + regex analyzer tests
      test_generators.py         Mermaid generator tests
      test_api.py                Scan API tests
      test_pattern_api.py        Pattern API tests
      test_determinism.py        ID generation tests
      test_ontology.py           SKOS ontology tests
      test_graph_service.py      Graph service tests (mocked)
      test_graph_api.py          Graph API endpoint tests

  frontend/
    package.json               Node dependencies
    vite.config.ts             Vite + React + Tailwind config
    tsconfig.app.json          TypeScript config
    index.html                 Entry HTML
    src/
      main.tsx                 React root mount
      App.tsx                  Router + nav + providers
      index.css                Tailwind base styles
      api/
        client.ts              Typed API client (all endpoints)
      pages/
        Dashboard.tsx          Scan form + scan history
        DiagramPage.tsx        Perspective diagram viewer with tabs
        KnowledgeGraphPage.tsx React Flow graph visualization
        PatternLibraryPage.tsx Pattern search + filter + grid
        PatternDetailPage.tsx  Pattern detail + status transitions
        PatternEditorPage.tsx  Markdown editor + live preview
        TemplatePage.tsx       Template creation + rendering
      components/
        MermaidRenderer.tsx    Self-healing Mermaid (4-level retry)
        DiagramTabs.tsx        Perspective tab switcher
        ScanForm.tsx           Repository URL input
        PatternCard.tsx        Pattern grid item
        StatusBadge.tsx        Status pill (stone/amber/emerald/red)
        MarkdownRenderer.tsx   Markdown with Mermaid block detection
        TemplateEditor.tsx     Template creation form
        PlaceholderForm.tsx    Template rendering form
```

---

## Tech Stack

### Backend

| Library | Purpose |
|---------|---------|
| [FastAPI](https://fastapi.tiangolo.com/) | Web framework with automatic OpenAPI docs |
| [Pydantic](https://docs.pydantic.dev/) | Data validation and serialization |
| [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | Environment-based configuration |
| [GitPython](https://gitpython.readthedocs.io/) | Repository cloning |
| [FalkorDB](https://www.falkordb.com/) | Graph database with Cypher queries |
| [Jinja2](https://jinja.palletsprojects.com/) | Template rendering |
| [certifi](https://github.com/certifi/python-certifi) | SSL certificate bundle fallback |

### Frontend

| Library | Purpose |
|---------|---------|
| [React 18](https://react.dev/) | UI framework |
| [TypeScript](https://www.typescriptlang.org/) | Type safety |
| [Vite](https://vitejs.dev/) | Build tool + dev server |
| [TanStack Query](https://tanstack.com/query) | Server state + caching |
| [React Router](https://reactrouter.com/) | Client-side routing |
| [React Flow](https://reactflow.dev/) (@xyflow/react v12) | Interactive graph canvas |
| [ELK](https://www.eclipse.org/elk/) (elkjs) | Hierarchical graph layout |
| [Mermaid](https://mermaid.js.org/) | Diagram-as-code rendering |
| [Tailwind CSS](https://tailwindcss.com/) | Utility-first styling |

---

## Testing

### Backend (95 tests)

```bash
cd backend
python -m pytest tests/ -v
```

Tests run entirely without FalkorDB. The graph service returns empty results when unavailable, and graph API tests isolate scan state.

Test coverage:
- AST analyzer entity and relationship extraction
- All four Mermaid generators (output + determinism)
- Scan, pattern, and template API endpoints
- Pattern status workflow transitions
- SKOS ontology completeness and consistency
- Graph service with mocked FalkorDB
- Graph API endpoints with graceful fallback

### Frontend

```bash
cd frontend
npx tsc --noEmit        # Type check
npx vite build          # Production build
```

---

## Deployment

### Docker Compose

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
    volumes:
      - falkordb_data:/data

volumes:
  falkordb_data:
```

### Production Checklist

- [ ] Set `PATTERNVIZ_CORS_ORIGINS` to your frontend domain
- [ ] Place a reverse proxy (nginx/Caddy) in front of both services
- [ ] Mount a volume for FalkorDB data persistence
- [ ] Set proxy variables if behind a corporate firewall
- [ ] Verify system CA store includes corporate root CAs if applicable

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Scan fails with SSL error** | Ensure `PATTERNVIZ_USE_SYSTEM_SSL=true` and your system CA store includes your corporate root CA |
| **Scan fails with proxy error** | Verify `PATTERNVIZ_HTTPS_PROXY` format: `http://host:port` or `http://user:pass@host:port` |
| **Diagram shows "auto-corrected"** | Expected for large codebases. Backend limits to 80 entities; frontend truncates to 60 lines |
| **Knowledge graph is empty** | Run a scan first. The graph populates from scan data (works without FalkorDB) |
| **FalkorDB won't connect** | Verify container is running: `docker ps \| grep falkordb`. Check port 6379 isn't used by Redis |
| **Tests fail with import errors** | Run `pip install -e ".[dev]"` from the `backend/` directory |
| **Frontend build fails** | Run `npm install` in `frontend/`. Check Node.js >= 18 |

---

## Documentation

| Document | Description |
|----------|-------------|
| [Features](docs/FEATURES.md) | Complete feature descriptions with API endpoint table |
| [User Guide](docs/USER_GUIDE.md) | Step-by-step walkthrough for every feature |
| [Developer Guide](docs/DEVELOPER_GUIDE.md) | Architecture, extending analyzers/perspectives, deployment, and design decisions |

---

## API Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/scan` | Scan a repository |
| `GET` | `/api/scan` | List all scans |
| `DELETE` | `/api/scan` | Clear all scans |
| `GET` | `/api/scan/{id}` | Get scan status |
| `GET` | `/api/scan/{id}/entities` | Raw entities and relationships |
| `GET` | `/api/scan/{id}/diagrams/{perspective}` | Mermaid diagram |
| `POST` | `/api/patterns` | Create pattern |
| `GET` | `/api/patterns` | Search patterns |
| `GET` | `/api/patterns/{id}` | Get pattern |
| `PUT` | `/api/patterns/{id}` | Update pattern |
| `DELETE` | `/api/patterns/{id}` | Delete pattern |
| `POST` | `/api/patterns/{id}/transition` | Change status |
| `GET` | `/api/patterns/template` | System design template |
| `POST` | `/api/templates` | Create template |
| `GET` | `/api/templates` | List templates |
| `POST` | `/api/templates/{id}/render` | Render template |
| `DELETE` | `/api/templates/{id}` | Delete template |
| `GET` | `/api/graph/status` | FalkorDB status |
| `GET` | `/api/graph/knowledge` | Knowledge graph data |
| `GET` | `/api/graph/concepts` | SKOS concept hierarchy |
| `GET` | `/api/graph/patterns/{id}/related` | Related patterns |
| `GET` | `/api/graph/stats` | Graph statistics |

Full API docs with interactive testing: `http://localhost:8000/docs` (Swagger UI).
