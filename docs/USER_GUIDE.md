# PatternViz User Guide

This guide walks through every feature of PatternViz from a user's perspective.

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Quick Start

```bash
# Clone the project
cd /path/to/patterns

# Backend
cd backend
pip install -e ".[dev]"
cp ../.env.example .env       # Edit proxy/FalkorDB settings as needed
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### Windows Setup

PatternViz works natively on Windows. The clone directory defaults to `%TEMP%\patternviz` and SSL certificates are auto-detected from Git for Windows or exported from the Windows certificate store.

```powershell
cd backend
pip install -e ".[dev]"
copy ..\.env.example .env
uvicorn app.main:app --reload
```

### Enterprise Network Setup

If you are behind a corporate proxy, edit `backend/.env`:

```env
PATTERNVIZ_HTTPS_PROXY=http://proxy.corp.example.com:8080
PATTERNVIZ_HTTP_PROXY=http://proxy.corp.example.com:8080
PATTERNVIZ_NO_PROXY=localhost,127.0.0.1
PATTERNVIZ_USE_SYSTEM_SSL=true
```

The `USE_SYSTEM_SSL=true` setting (enabled by default) makes Git use your OS certificate store. This works on all platforms:
- **Windows:** Auto-detects Git for Windows CA bundle, or exports certificates from the Windows certificate store via PowerShell
- **macOS:** Uses `/etc/ssl/cert.pem` or Homebrew OpenSSL bundles
- **Linux:** Uses distribution-specific CA paths (Debian, RHEL, Alpine, etc.)
- **Fallback:** Python's built-in `certifi` bundle (always available)

### Custom SSL Certificate Paths

If auto-detection does not find your corporate CA, specify the path explicitly:

```env
# Point to your corporate CA bundle (PEM format)
PATTERNVIZ_SSL_CA_FILE=C:\certs\corporate-ca-bundle.pem        # Windows
PATTERNVIZ_SSL_CA_FILE=/etc/pki/tls/certs/ca-bundle.crt        # Linux

# Or point to a directory of individual CA certificates
PATTERNVIZ_SSL_CA_PATH=C:\certs\ca-dir                         # Windows
PATTERNVIZ_SSL_CA_PATH=/etc/ssl/certs                           # Linux
```

When `SSL_CA_FILE` is set and the file exists, it takes priority over auto-detection.

---

## Scanning a Repository

1. Navigate to the **Dashboard** (home page)
2. Enter a Git repository URL (e.g., `https://github.com/user/repo`)
3. Optionally change the branch (defaults to `main`)
4. Click **Scan Repository**

The scan clones the repository, analyzes all supported files, and generates four architectural diagrams. When complete, you are redirected to the diagram viewer.

### What Happens During a Scan

1. The repository is shallow-cloned (depth=1) to a temporary directory
2. All files are walked, skipping `node_modules`, `__pycache__`, `.venv`, etc.
3. Python files are parsed with full AST analysis; other files use regex patterns
4. Entities (classes, functions, endpoints, etc.) and relationships are extracted
5. Four perspective analyzers filter the results into focused views
6. Mermaid generators produce diagram code for each perspective
7. If FalkorDB is connected, entities and relationships are stored in the graph
8. The temporary clone is cleaned up

---

## Viewing Diagrams

After scanning, the **Diagram Page** shows four perspective tabs. Each perspective has two view modes, toggled via the **Graph** / **Mermaid** buttons in the top right:

- **Graph view** (default) — Interactive React Flow visualization with ELK layout. Zoom, pan, drag nodes, toggle horizontal/vertical layout. Color-coded entity nodes with type legends and minimap.
- **Mermaid view** — Traditional Mermaid diagram rendering. Click **Copy Mermaid Code** to paste into GitHub, Notion, Confluence, or any Mermaid-compatible tool.

### Ingestion
How data enters the system. API endpoints, message consumers, and file readers appear as entry nodes with their downstream calls.

### ER Diagram
Structural view of classes and models. Shows inheritance, containment, and associations. In Graph view, each entity is a draggable node. In Mermaid view, uses standard ER notation with attribute and method listings.

### Transformation
The processing pipeline. Shows functions, database operations, and file I/O that transform data between ingestion and output.

### Output
Where data goes. Database writes, file writers, and message producers are grouped by type.

### Large Diagrams

When a diagram has too many entities to render cleanly:
- The backend keeps only the 80 most-connected entities
- The frontend retries with sanitized, simplified, or truncated code
- A yellow notice appears when auto-correction was applied

---

## Pattern Library

Navigate to **Pattern Library** in the top nav.

### Creating a Pattern

1. Click **New Pattern**
2. Fill in the metadata: Title, Description, Owner, Tags (comma-separated)
3. Write content in the editor using Markdown
4. Embed Mermaid diagrams inside ` ```mermaid ` code fences
5. The right pane shows a live preview
6. Click **Save**

### System Design Template

New patterns are pre-filled with a system design template containing sections for Overview, Context, Solution Architecture, Components, Data Flow, API Contracts, Decision Log, Trade-offs, and References — each with placeholder Mermaid diagrams.

### Searching Patterns

Use the filter row at the top of the Pattern Library:
- **Search** — Matches against title, description, and content
- **Status** — Filter by Draft, Review, Approved, or Deprecated
- **Owner** — Filter by team or author name
- **Tags** — Comma-separated; with FalkorDB, searches include related SKOS concepts

### Managing Pattern Status

On a pattern detail page, the available status transitions appear as buttons:
- Draft can move to Review
- Review can move to Approved or back to Draft
- Approved can move to Deprecated
- Deprecated can return to Draft

### Related Patterns

When FalkorDB is connected, the bottom of each pattern detail page shows related patterns that share tags or are linked to the same scan.

### Creating a Pattern from a Scan

Use the API endpoint `POST /api/patterns/from-scan/{scan_id}` to create a pattern pre-filled with all four perspective diagrams from a scan.

---

## Knowledge Graph

Navigate to **Knowledge Graph** in the top nav.

### Controls

- **Search** — Filter nodes by name
- **Scan dropdown** — View entities from a specific scan or all scans
- **Layout toggle** — Switch between Horizontal and Vertical ELK layout
- **Legend** — Click entity type buttons to show/hide specific types

### Interacting with the Graph

- **Zoom:** Scroll wheel or pinch gesture
- **Pan:** Click and drag on the background
- **Move nodes:** Click and drag individual nodes
- **Minimap:** The bottom-right minimap shows the full graph; click to navigate
- **Zoom controls:** Use the +/- buttons in the bottom-left corner
- **Fit view:** The graph auto-fits on load; use the fit button to reset

### Node Colors

Each entity type has a distinct color:

| Type | Color | Description |
|------|-------|-------------|
| class | Purple | Class definitions |
| function | Green | Standalone functions |
| method | Light green | Class methods |
| endpoint | Blue | API endpoints |
| model | Pink | Data models |
| db_read | Cyan | Database read operations |
| db_write | Red | Database write operations |
| file_reader | Green | File read operations |
| file_writer | Pink | File write operations |
| consumer | Orange | Message consumers |
| producer | Rose | Message producers |

### Edge Types

- **calls** — Function/method invocations (animated)
- **inherits** — Class inheritance
- **contains** — Containment (class has method)
- **uses** — Usage relationship
- **reads/writes** — Data I/O
- **produces/consumes** — Message passing

---

## Templates

Navigate to **Templates** in the top nav.

### Creating a Template

1. Enter a template name
2. Select a perspective (ingestion, er, transformation, output)
3. Write Mermaid code using `{{ placeholder }}` syntax for variable parts
4. Click **Save Template**

### Rendering a Template

1. Click a saved template name in the list
2. Fill in the placeholder values in the right panel
3. Click **Render**
4. The rendered Mermaid diagram appears below

### Example Template

```
graph TD
    {{ service_name }}["{{ service_label }}"]
    {{ service_name }} --> DB["{{ database }}"]
    {{ service_name }} --> Cache["{{ cache_system }}"]
```

---

## Tips

- **Deterministic scans:** Scanning the same repo and branch produces the same scan ID, so you can re-scan to update diagrams
- **Mermaid everywhere:** All diagrams use standard Mermaid syntax; copy and paste into any tool that supports it
- **FalkorDB is optional:** Everything works without it; the knowledge graph uses in-memory data from scans as a fallback
- **Proxy support:** Set `PATTERNVIZ_HTTPS_PROXY` once and all scans route through your corporate proxy
