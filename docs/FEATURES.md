# PatternViz Features

PatternViz is a code pattern visualization tool that scans repositories, extracts code entities and relationships via AST analysis, and generates interactive diagrams across multiple architectural perspectives.

---

## Repository Scanning

Scan any Git repository by URL. PatternViz clones the repo (shallow, depth=1), walks every file the analyzer registry supports, and extracts a structured graph of code entities and their relationships.

**Supported languages:** Python (full AST analysis), with generic regex fallback for other file types.

**What gets extracted:**
- Classes, functions, methods, variables
- API endpoints (Flask/FastAPI route decorators)
- Database operations (reads, writes)
- File I/O (readers, writers)
- Message producers and consumers
- Relationships: calls, inherits, imports, uses, contains, produces, consumes, reads, writes

**Enterprise proxy support:** Configure `PATTERNVIZ_HTTPS_PROXY` in `backend/.env` to clone repos through a corporate proxy. System SSL certificates are used by default, which handles TLS-inspecting proxies with custom root CAs.

---

## Four Architectural Perspectives

Every scan generates four Mermaid diagrams, each filtering the entity graph through a different architectural lens:

### Ingestion
Shows data entry points: API endpoints, message consumers, and file readers. Reveals how data enters the system.

### Entity-Relationship (ER)
Shows structural relationships between classes and models. Displays inheritance hierarchies, containment, and associations using Mermaid ER diagram syntax with attributes and methods.

### Transformation
Shows the processing pipeline between data ingestion and output. Includes functions, database reads/writes, and file operations that transform data.

### Output
Shows data sinks: database writes, file writers, and message producers. Reveals where processed data goes.

---

## Pattern Library

A document-based pattern catalog for capturing architectural decisions, system designs, and reusable patterns.

### Pattern Lifecycle
Each pattern follows a status workflow:
- **Draft** — Initial creation, editable
- **Review** — Submitted for team review
- **Approved** — Accepted as a standard pattern
- **Deprecated** — Superseded, kept for reference

Transitions are enforced: Draft to Review to Approved to Deprecated, with the ability to return to Draft from Review or Deprecated.

### Markdown + Mermaid Editor
Patterns use Markdown content with embedded Mermaid diagram blocks. The editor provides a live split-pane preview that renders both Markdown and Mermaid in real time.

### Search and Filtering
Search patterns by text query (searches title, description, and content), filter by status, owner, or tags. When FalkorDB is connected, tag searches use SKOS concept traversal to find patterns tagged with related concepts.

### Scan-Linked Patterns
Create a pattern directly from a scan result. The generated pattern includes all four perspective diagrams embedded as Mermaid blocks.

---

## Knowledge Graph

An interactive graph visualization of all code entities and their relationships, powered by React Flow with ELK hierarchical layout.

### Features
- **ELK layout engine** with horizontal or vertical direction toggle
- **Custom entity nodes** color-coded by type (class, function, endpoint, db_read, etc.)
- **Interactive canvas:** zoom, pan, drag nodes, minimap navigation
- **Filtering:** search by name, filter by entity type via the legend, filter by scan
- **Grouped layout:** entities are clustered by ontology category (CodeConstruct, APIElement, DataAccessor, MessageHandler)

### SKOS Ontology
Entities are organized into a W3C SKOS concept hierarchy:
- **CodeConstruct** — class, function, method, variable
- **APIElement** — endpoint, model
- **DataAccessor** — db_read, db_write, file_reader, file_writer
- **MessageHandler** — consumer, producer

This hierarchy powers semantic tag searching in the pattern library.

### Data Sources
- **FalkorDB connected:** Queries the graph database directly with Cypher
- **FalkorDB offline:** Falls back to in-memory scan data automatically

---

## Mermaid Templates

Create reusable Mermaid diagram templates with `{{ placeholder }}` syntax. Fill in placeholders to generate customized diagrams.

### Workflow
1. Create a template with a name, perspective, and Mermaid content using `{{ variable }}` placeholders
2. Select a saved template
3. Fill in the placeholder values
4. Render the final Mermaid diagram

---

## Self-Healing Diagrams

Large or complex Mermaid code is automatically repaired when rendering fails:

1. **Raw render** — Try the original code
2. **Sanitized** — Fix unbalanced quotes, prefix numeric IDs
3. **Simplified** — Strip complex node shapes to rectangles
4. **Truncated** — Keep only the 60 most relevant lines, preserving subgraph structure

The backend also limits diagrams to 80 entities (keeping the most-connected ones) and escapes all special characters in IDs and labels.

---

## FalkorDB Knowledge Graph (Optional)

When FalkorDB is running, PatternViz stores all entities, relationships, and patterns in a persistent graph database:

- **SKOS concept nodes** with BROADER/NARROWER edges enable semantic tag traversal
- **Pattern search** finds patterns tagged with narrower (more specific) concepts
- **Related patterns** discovers patterns sharing tags, linked to the same scan, or connected to the same entities
- **Perspective queries** use Cypher instead of in-memory filtering

### Setup
```bash
docker run -p 6379:6379 falkordb/falkordb
```

Set `PATTERNVIZ_FALKORDB_ENABLED=true` in `backend/.env` (this is the default).

---

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scan` | POST | Scan a repository |
| `/api/scan` | GET | List all scans |
| `/api/scan` | DELETE | Clear all scans |
| `/api/scan/{id}` | GET | Get scan status |
| `/api/scan/{id}/entities` | GET | Get raw entities and relationships |
| `/api/scan/{id}/diagrams/{perspective}` | GET | Get Mermaid diagram |
| `/api/patterns` | POST | Create pattern |
| `/api/patterns` | GET | Search patterns |
| `/api/patterns/{id}` | GET/PUT/DELETE | Pattern CRUD |
| `/api/patterns/{id}/transition` | POST | Change pattern status |
| `/api/patterns/template` | GET | Get system design template |
| `/api/templates` | POST/GET | Template CRUD |
| `/api/templates/{id}/render` | POST | Render template |
| `/api/graph/status` | GET | FalkorDB connection status |
| `/api/graph/knowledge` | GET | Knowledge graph nodes and edges |
| `/api/graph/concepts` | GET | SKOS concept hierarchy |
| `/api/graph/patterns/{id}/related` | GET | Related patterns |
| `/api/graph/stats` | GET | Graph statistics |
