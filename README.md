# ZenAI — The Living Archive of Zendrix

> A desktop AI-powered worldbuilding operating system for the Zendrix multiverse paracosm.

ZenAI is not a chatbot. It is a **second brain** — a local desktop application that stores, organizes, analyzes, visualizes, expands, and evolves an entire multiverse lore database, powered by Claude AI.

---

## What is Zendrix?

- **Zendrix Tree** — the master cosmic structure
- **Fruits** — individual Universes hanging from the Tree, each with their own characters, factions, locations, events, and history
- **Root Entities** — unique multiversal beings (OM_X, K, _LA, Zendrix Tree itself) that exist across ALL universes and are never duplicated

---

## Features (Planned)

| Module | Feature | Status |
|---|---|---|
| 1 | Database — 21-table SQLite schema + full CRUD + CSV I/O | ✅ Done |
| 2 | Document Ingestion — DOCX/PDF/TXT → entity extraction pipeline | ❌ |
| 3 | Knowledge Graph — NetworkX + PyVis, 4 graph types | ❌ |
| 4 | Timeline Engine — multiverse → universe → character → event zoom | ❌ |
| 5 | AI Core — Claude-powered lore generation, consistency checking, trait analysis | ❌ |
| 6 | Vector Search — FAISS + Sentence Transformers semantic search | ❌ |
| 7 | Wiki Generator — auto Wikipedia-style pages per entity | ❌ |
| 8 | UI Shell — PySide6 desktop app with full sidebar navigation | ❌ |
| 9 | Cosmic View — interactive Zendrix Tree visualization | ❌ |
| 10 | Analytics — DB stats, growth charts, version history, canon management | ❌ |
| 11 | Story Assistant — AI story/chapter/dialogue writer constrained to lore | ❌ |
| 12 | World Simulation Engine — "what if X happened?" cascade predictor | ❌ |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Desktop UI | PySide6 |
| Database | SQLite + SQLAlchemy |
| Knowledge Graph | NetworkX |
| Graph Visualization | PyVis + Plotly |
| AI Backend | Claude API (Anthropic) |
| Embeddings | Sentence Transformers |
| Vector Search | FAISS |
| Document Processing | python-docx, PyMuPDF |

---

## Project Structure

```
ZenAI/
├── app/
│   ├── database/        # Schema, DB init, CRUD layer, CSV I/O
│   ├── ai/              # Claude integration (lore gen, story writer, etc.)
│   ├── graph/           # Knowledge graph engine
│   ├── lore/            # Document ingestion pipeline
│   ├── timeline/        # Timeline engine
│   ├── search/          # FAISS vector search
│   ├── wiki/            # Wiki page generator
│   ├── simulation/      # World simulation engine
│   └── ui/              # PySide6 UI shell + widgets
├── data/
│   ├── lore/            # Generated wiki pages
│   ├── uploads/         # User-uploaded documents
│   ├── cache/           # FAISS index cache
│   └── zenai.db         # SQLite database (auto-created)
├── config/              # .env + app settings
├── docs/
│   └── er_diagram.mmd   # Full ER diagram (view at mermaid.live)
├── main.py              # App entry point
└── requirements.txt
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/ZenAI.git
cd ZenAI
```

### 2. Create virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `config/.env` file:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

### 5. Initialize the database

```bash
python -m app.database.db_init
```

This creates `data/zenai.db` and seeds the 4 root entities (OM_X, K, _LA, Zendrix Tree).

### 6. Run the app

```bash
python main.py
```

---

## Database

The schema has **21 tables** covering every aspect of the Zendrix multiverse:

- Universes + inter-universe connections
- Root Entities + their cross-universe links
- Characters (with variant/alternate version support)
- Factions, Locations, Artifacts, Powers
- Events + participants
- Character relationships (graph edges)
- Stories + Simulation Runs
- Lore Documents (ingestion pipeline)
- Version History (full rollback support)
- Tags + Notes (on any entity)

Every major entity has:
- `id` — auto-increment int (fast joins)
- `uuid` — prefixed string e.g. `chr_8f4a1b2c...` (global reference)
- `canon_status` — canon / non_canon / alt_timeline / experimental
- `importance_score` — 1 to 100

View the full ER diagram: paste `docs/er_diagram.mmd` into [mermaid.live](https://mermaid.live)

---

## CSV Import / Export

```python
from app.database.db_init import get_session
from app.database.csv_io import export_csv, import_csv, export_all_tables

session = get_session()

# Export one table
export_csv(session, "characters", "data/exports/characters.csv")

# Import from CSV
import_csv(session, "characters", "data/imports/characters.csv")

# Export everything
export_all_tables(session, "data/exports/")
```

---

## Naming Conventions

| Entity | UUID Prefix |
|---|---|
| Character | `chr_` |
| Universe | `uni_` |
| Faction | `fac_` |
| Location | `loc_` |
| Event | `evt_` |
| Artifact | `art_` |
| Story | `sty_` |
| Root Entity | `root_` |

| Field | Values |
|---|---|
| `canon_status` | canon, non_canon, alt_timeline, experimental |
| `story_mode` | canon, non_canon, what_if, alt_timeline, rpg_sim |
| `edge_type` | friend, enemy, family, mentor, student, created, destroyed, owns, located_in, participated_in |
| `event_type` | birth, death, rebirth, war, other |
| `importance_score` | 1–100 (OM_X = 100, Raven ≈ 75, random soldier ≈ 5) |

---

## License

MIT License — see `LICENSE` for details.
