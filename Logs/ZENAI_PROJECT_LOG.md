# ZEN AI — "The Living Archive of Zendrix"
## PROJECT LOG / STATUS DOCUMENT
### Generated: Phase 0 Complete — Use this as your single source of truth

---

# 1. PROJECT OVERVIEW

**Zen AI** is a desktop AI-powered worldbuilding operating system for the Zendrix multiverse paracosm. It is NOT a chatbot — it's a "second brain" that stores, organizes, analyzes, visualizes, expands, and evolves the entire Zendrix lore database.

## Zendrix Cosmology (core concept to remember)
- **Zendrix Tree** = the master structure
- **Fruits on the Tree** = Universes (each universe has its own characters, factions, locations, events, history)
- **Root Entities** = unique multiversal entities that exist ACROSS all universes, never duplicated. Known examples: `OM_X`, `K`, `_LA`, `Zendrix Tree`

---

# 2. TECH STACK (FINAL — DO NOT CHANGE WITHOUT REASON)

| Layer | Technology |
|---|---|
| Language | Python |
| Desktop UI | PySide6 |
| Database | SQLite + SQLAlchemy (ORM) |
| Knowledge Graph | NetworkX |
| Graph Visualization | PyVis (+ Plotly for charts) |
| AI Backend | Claude API (anthropic package) |
| Embeddings | Sentence Transformers |
| Vector Search | FAISS |
| Document Processing | python-docx (DOCX), PyMuPDF (PDF) |
| Architecture style | Modular, scalable, offline-first |

---

# 3. FOLDER STRUCTURE (ALREADY CREATED)

```
ZenAI/
├── app/
│   ├── __init__.py
│   ├── ui/                  (empty - Module 8 & 9)
│   │   └── __init__.py
│   ├── database/            (DONE - Module 1)
│   │   ├── __init__.py
│   │   ├── models.py         ✅ COMPLETE
│   │   └── db_init.py        ✅ COMPLETE
│   │   └── crud/              ❌ NOT CREATED YET
│   │   └── csv_io.py          ❌ NOT CREATED YET
│   ├── ai/                  (empty - Module 5)
│   │   └── __init__.py
│   ├── graph/                (empty - Module 3)
│   │   └── __init__.py
│   ├── lore/                 (empty - Module 2)
│   │   └── __init__.py
│   ├── timeline/             (empty - Module 4)
│   │   └── __init__.py
│   ├── wiki/                 (empty - Module 7)
│   │   └── __init__.py
│   ├── search/               (empty - Module 6)
│   │   └── __init__.py
│   └── simulation/           (empty - Module 12)
│       └── __init__.py
│
├── data/
│   ├── lore/                 (for wiki output etc.)
│   ├── uploads/              (user-uploaded docx/pdf/txt/md)
│   ├── cache/                (FAISS index etc.)
│   └── zenai.db              (created when db_init.py runs)
│
├── config/                    ❌ NOT CREATED YET (for Claude API key, settings)
├── docs/
│   └── er_diagram.mmd        ✅ COMPLETE
├── main.py                    ❌ NOT CREATED YET (app entry point)
├── requirements.txt           ✅ COMPLETE
└── README.md                  ✅ COMPLETE
```

---

# 4. WHAT IS 100% DONE (PHASE 0)

## ✅ 4.1 — Database Schema (FROZEN — do not redesign)

File: `app/database/models.py`

**21 Tables total, all built in SQLAlchemy:**

1. **universes** — id, uuid, name, description, canon_status, importance_score, created_at, updated_at
2. **universes_connections** — id, source_universe_id (FK), target_universe_id (FK), connection_type, description
3. **root_entities** — id, uuid, name, type, description, notes, importance_score
4. **root_entity_links** — id, root_entity_id (FK), entity_type, entity_id, description
5. **characters** — id, uuid, universe_id (FK), name, titles, aliases, species, traits_json, personality, motivations, goals, ideology, canon_status, importance_score, version, parent_character_id (FK self-reference for variants), created_at, updated_at
6. **factions** — id, uuid, universe_id (FK), name, founder_id (FK→characters), ideology, description, canon_status, importance_score
7. **locations** — id, uuid, universe_id (FK), name, description, type, canon_status, importance_score
8. **powers** — id, name, description, rules, scope ('universal'/'local')
9. **character_powers** — character_id (FK), power_id (FK), proficiency (0-100)
10. **events** — id, uuid, universe_id (FK), name, description, date_value, date_label, event_type (birth/death/rebirth/war/other), canon_status, importance_score
11. **event_participants** — id, event_id (FK), entity_type, entity_id, role
12. **relationships** — id, character_a_id (FK), character_b_id (FK), edge_type, description
    - edge_type values: friend, enemy, family, mentor, student, created, destroyed, owns, located_in, participated_in
13. **artifacts** — id, uuid, universe_id (FK), name, description, owner_id (FK→characters), powers_json, importance_score
14. **stories** — id, uuid, title, summary, raw_text, story_mode, canon_status, universe_id (FK), created_at
    - story_mode values: canon, non_canon, what_if, alt_timeline, rpg_sim
15. **simulation_runs** — id, title, premise, affected_entities_json, generated_outcomes_json, reasoning_text, universe_id (FK), created_at
16. **lore_documents** — id, filename, raw_text, processed, upload_date
17. **version_history** — id, entity_type, entity_id, version_number, data_snapshot_json, timestamp, approved_by
18. **tags** — id, name
19. **entity_tags** — id, entity_type, entity_id, tag_id (FK→tags)
20. **entity_notes** — id, entity_type, entity_id, note_text, created_at

**Key design decisions:**
- Every major entity (universes, characters, factions, locations, events, artifacts, stories, root_entities) has BOTH:
  - `id` (auto-increment int, for fast internal joins)
  - `uuid` (prefixed string like `chr_8f4a1b2c...`, `evt_...`, `fac_...`, `uni_...`, `art_...`, `sty_...`, `root_...` — for global unique reference, avoids "Character #15 vs Faction #15" confusion)
- `canon_status` field exists on all major entities: canon / non_canon / alt_timeline / experimental
- `importance_score` (1-100) exists on all major entities — used for Cosmic View highlighting
- `traits_json` on characters stores AI-inferred trait percentages, e.g. `{"Strategic": 92, "Ruthless": 80}`

## ✅ 4.2 — Database Initialization

File: `app/database/db_init.py`

- Creates SQLite DB at `data/zenai.db`
- `init_db()` function creates all tables
- Auto-seeds 4 root entities on first run: **OM_X, K, _LA, Zendrix Tree** (so they always exist and are never duplicated)
- `get_session()` returns a SQLAlchemy session for use anywhere in the app
- **TESTED AND WORKING** — confirmed root entities seed correctly

## ✅ 4.3 — ER Diagram

File: `docs/er_diagram.mmd` (Mermaid format)

- Paste content into https://mermaid.live to view visually
- Shows all 21 tables and their relationships (FKs, one-to-many, many-to-many)

## ✅ 4.4 — requirements.txt

```
PySide6
SQLAlchemy
networkx
pyvis
plotly
anthropic
sentence-transformers
faiss-cpu
python-docx
PyMuPDF
python-dotenv
pandas
```

## ✅ 4.5 — README.md

Basic setup instructions:
```bash
pip install -r requirements.txt
python -m app.database.db_init
```

---

# 5. WHAT IS NOT DONE YET — FULL ROADMAP

## ❌ 5.1 — Module 1 remainder: CRUD Layer + CSV I/O

**Location:** `app/database/crud/` (folder not created yet) + `app/database/csv_io.py`

**What it needs:**
- CRUD functions for EVERY table (create, read, update, delete, list/filter)
  - Suggested structure: one file per entity group, e.g. `crud/characters.py`, `crud/universes.py`, `crud/events.py`, etc., OR one `crud.py` with functions organized by entity
- Each CRUD write operation should ALSO write a snapshot to `version_history` table (for rollback)
- `csv_io.py`:
  - `export_csv(table_name)` — dumps any table to CSV
  - `import_csv(table_name, file_path)` — bulk load/validate CSV into a table
- This is the FOUNDATION every other module depends on — **build this FIRST**

---

## ❌ 5.2 — Module 5: AI Core (Claude Integration)

**Location:** `app/ai/`

**Split into 4 separate services (NOT one giant prompt):**

1. **`claude_client.py`** — shared wrapper
   - Handles Claude API calls, retries, error handling
   - Parses JSON responses (strip ```json fences etc.)

2. **`context_builder.py`** — shared helper
   - Before any AI generation, pulls relevant existing DB entries (by universe_id, entity_id, related entities) so AI output fits canon

3. **`lore_generator.py`**
   - Generates: new factions, worlds/universes, characters, events, story arcs, mythology, artifacts
   - Must return structured JSON matching the DB schema
   - All output goes through Approve/Reject/Edit flow → if approved, write via CRUD layer (5.1) + update graphs/timelines/relationships

4. **`consistency_checker.py`**
   - Detects contradictions: character dead but appears alive later, conflicting origins, power inconsistencies, timeline inconsistencies
   - Generates warnings

5. **`trait_analyzer.py`**
   - Given character lore text, infers trait percentages (e.g. Strategic: 92%, Ruthless: 80%)
   - Stores into `characters.traits_json`

6. **`story_writer.py`**
   - Generates chapters, dialogues, story arcs
   - Must remain consistent with lore database (uses context_builder)
   - Feeds into Module 11 (Story Assistant)

**Note:** Future Prediction Engine logic is NOT part of this module — it belongs to Module 12 (World Simulation Engine).

---

## ❌ 5.3 — Module 2: Document Ingestion Engine

**Location:** `app/lore/`

**3-Phase Pipeline (to reduce API costs):**

- **Phase 1 — Regex/Pattern Extraction** (free, fast, local)
  - Detect capitalized names, match against existing DB entity names, detect date patterns
  - Produces candidate list
  
- **Phase 2 — Claude Extraction** (only on Phase 1 candidates + surrounding context)
  - Send filtered chunks to Claude (via `lore_generator.py` or dedicated extraction prompt)
  - Extract: characters, factions, locations, powers, events, relationships as structured JSON

- **Phase 3 — Human Review**
  - Show staged/extracted entities in UI
  - User can Approve / Reject / Edit
  - On approval → write to DB via CRUD layer, mark `lore_documents.processed = true`

**File readers needed:**
- DOCX → python-docx
- PDF → PyMuPDF
- TXT/MD → plain file read

---

## ❌ 5.4 — Module 3: Knowledge Graph Engine

**Location:** `app/graph/`

**Build using NetworkX, render using PyVis. 4 graph types:**

1. **Universe Graph** — all entities inside one universe_id, edges = relationships/memberships
2. **Character Graph** — one character as center node, edges to: friends, enemies, family, mentors, students, factions, events
3. **Multiverse Graph** — nodes = universes, edges from `universes_connections` table
4. **Root Entity Graph** — root entity as center, edges from `root_entity_links` table to everything it touches

**Standardized edge types** (used across all graphs, from `relationships.edge_type`):
`friend, enemy, family, mentor, student, created, destroyed, owns, located_in, participated_in`

- Render each graph to HTML via PyVis
- Refresh/rebuild graph whenever underlying DB data changes (hook into CRUD write operations)

---

## ❌ 5.5 — Module 4: Timeline Engine

**Location:** `app/timeline/`

**Hierarchy:**
```
Multiverse Timeline
  └─ Universe Timeline
       └─ Character Timeline
            └─ Event Timeline
```

- Pull from `events` table + character birth/death info + optionally `simulation_runs` for hypothetical overlays
- Sort chronologically by `date_value`
- Function signature: `get_timeline(scope, id)` where scope ∈ {multiverse, universe, character, event}
- Output: list of `{date, label, type, entity_refs}` ready for UI timeline widget
- Support zoom from multiverse level down to character/event level

---

## ❌ 5.6 — Module 6: Vector Search & Semantic Search

**Location:** `app/search/`

**Categories:** characters, factions, locations, events, artifacts, stories

**Hybrid search (Exact + Semantic):**
- On every entity create/update → generate embedding via Sentence Transformers from text fields
- Store embeddings in FAISS index at `data/cache/faiss_index`
- Maintain ID mapping between FAISS positions and DB ids
- `search(query, type=None)` — semantic search across all categories
- `search_exact(category, field, value)` — exact field search (name/trait/faction/power/universe/keyword)
- Combine results: exact matches ranked first, then semantic, deduplicated
- `rebuild_index()` function for bulk re-embedding (needed after CSV imports etc.)

---

## ❌ 5.7 — Module 7: Wiki Generator

**Location:** `app/wiki/`

- For every entity type (character, faction, location, artifact, event), define a template (Markdown or HTML)
- Pull entity data + related entities via:
  - `relationships` table
  - `root_entity_links` table
  - `event_participants` table
  - `character_powers` table
  - `universes_connections` table
- Auto-generate a "Related" / cross-link section (Wikipedia-style)
- Render filled template → save to `data/lore/wiki/{type}/{id}.md`
- Regenerate automatically when entity is updated
- `get_wiki_page(entity_type, id)` function for UI display

---

## ❌ 5.8 — Module 8: UI Shell (PySide6)

**Location:** `app/ui/`

**Sidebar navigation (FINAL list):**
```
Dashboard | Universes | Characters | Factions | Locations | Artifacts
Events | Stories | Timeline | Graphs | Cosmic View | Search
AI Assistant | World Simulation | Lore Upload | Settings
```

- Main window with sidebar, each item = a QWidget page
- Each entity page: list/table view (from CRUD layer) + detail panel + edit forms
- Approve/Reject/Edit dialogs for AI-generated content (connects to Module 5)
- **Settings page:** Claude API key config, canon filter defaults, FAISS rebuild trigger button
- Wires all buttons/actions to other modules' functions

---

## ❌ 5.9 — Module 9: Cosmic View & Graph/Timeline Widgets

**Location:** `app/ui/cosmic/`, `app/ui/graphs/`

**Cosmic View** — the signature feature / master navigation screen:
```
Zendrix Tree
│
├── Fruit Alpha (Universe)
├── Fruit Beta (Universe)
├── Fruit Gamma (Universe)
│
└── Root Layer (OM_X, K, _LA, Zendrix Tree)
```

**Interaction spec:**
- Single click on a Fruit/Universe node → opens Universe detail page
- Double click on a Fruit/Universe node → opens Universe Graph (Module 3, filtered)
- Click on Root Layer node → opens Root Entity Graph
- Render via PyVis or custom QGraphicsScene; node positions informed by `universes_connections` adjacency
- Important entities (high `importance_score`) auto-highlighted

**Graph widget** — embeds PyVis HTML output in QWebEngineView, with a switcher for the 4 graph types (Universe/Character/Multiverse/Root Entity)

**Timeline widget** — visual timeline (QGraphicsView or Plotly HTML embed) showing Module 4 data, with zoom controls

---

## ❌ 5.10 — Module 10: Analytics, Memory & Canon Management

**Location:** `app/lore/memory/`, `app/ui/analytics/`

**Analytics dashboard:**
- Counts via DB queries: characters, universes, events, wars (event_type=war), artifacts, stories, power systems
- Growth-over-time charts using Plotly (x-axis = created_at)
- Canon filter toggle applies to all charts

**Version history viewer:**
- List versions per entity from `version_history` table
- Rollback button → restores a previous `data_snapshot_json`

**Canon management:**
- Filter/toggle views by `canon_status` across all modules
- Warning shown before any cross-canon operations (e.g. linking a canon character to a non-canon event)

---

## ❌ 5.11 — Module 11: AI Story Assistant

**Location:** `app/ai/story/`

- Takes a user prompt (e.g. "write a scene between Raven Prime and OM_X")
- Uses `context_builder.py` to pull both characters' full profiles + relationships + relevant events
- Sends to Claude via `story_writer.py`, constrained to existing lore facts
- Returns chapter/dialogue/arc text

**Story modes** (drives prompt template selection):
- `canon` — must match all existing lore exactly
- `non_canon` — relaxed consistency checking
- `what_if` — explicit premise injected ("what if X happened instead of Y")
- `alt_timeline` — branches from a specific event, diverges after
- `rpg_sim` — interactive, turn-based, user makes choices mid-generation

- Output saved to `stories` table with the chosen `story_mode`

---

## ❌ 5.12 — Module 12: World Simulation Engine

**Location:** `app/simulation/`

**This depends on Modules 1, 3, 4, 5 being functional — build LAST**

**Input:** a premise, e.g. "What happens if Raven dies?"

**Pipeline:**
1. Identify affected entities — query `relationships`, `event_participants`, `character_powers` for everything connected to the target entity
2. `context_builder.py` assembles full profile of target + all connected entities + relevant events
3. Send to Claude with simulation prompt: "Given this premise and lore context, predict cascading outcomes with reasoning"
4. Claude returns `outcomes` JSON: list of `{affected_entity, predicted_change, probability, reasoning}`
5. Store result in `simulation_runs` table
6. UI shows results as branching tree/list
7. User can approve outcomes →
   - Option A: spawn a `stories` entry (what_if mode)
   - Option B: write changes to actual entities (with explicit confirmation, since this is speculative)

---

## ❌ 5.13 — Other Missing Pieces (not full modules, but needed)

- **`config/`** folder — store Claude API key (via `.env` + `python-dotenv`), app settings (default canon filter, etc.)
- **`main.py`** — application entry point, launches PySide6 main window
- **Lore Consistency Checker** (mentioned in original spec) — covered by `consistency_checker.py` in Module 5
- **Missing Lore Detector** (mentioned in original spec) — needs its own function, likely in Module 5 or as a scheduled scan:
  - Detects: faction with no founder, character with no goals, universe with no history, etc.
  - Generates suggestions
- **Future Prediction Engine** (mentioned in original spec) — folded into Module 12 (World Simulation Engine)

---

# 6. RECOMMENDED BUILD ORDER (for parallel AI assignment)

```
STEP 1 (BLOCKS EVERYTHING):
  └─ 5.1 CRUD Layer + CSV I/O (app/database/crud/, csv_io.py)

STEP 2 (parallel, once Step 1 done):
  ├─ 5.2 Module 5 — AI Core (4 services)
  └─ 5.6 Module 6 — Search/FAISS

STEP 3 (parallel, depends only on Step 1):
  ├─ 5.3 Module 2 — Ingestion
  ├─ 5.4 Module 3 — Graph
  ├─ 5.5 Module 4 — Timeline
  └─ 5.7 Module 7 — Wiki

STEP 4:
  └─ 5.8 Module 8 — UI Shell (integrates everything as it completes)
  └─ 5.13 main.py + config/

STEP 5 (depends on Step 3's Graph + Timeline):
  ├─ 5.9 Module 9 — Cosmic View
  └─ 5.10 Module 10 — Analytics

STEP 6 (depends on Step 2's AI Core):
  └─ 5.11 Module 11 — Story Assistant

STEP 7 (LAST — depends on Steps 1, 3, 5, 2):
  └─ 5.12 Module 12 — World Simulation Engine
```

---

# 7. HOW TO RESUME WORK (for any AI / developer picking this up)

1. Read this file fully (you're doing it now ✅)
2. Open `app/database/models.py` — this is the FROZEN schema, every other module reads/writes through these models. **Do not change table structures** without updating this log.
3. Run `python -m app.database.db_init` to create/verify the DB
4. Pick the next item from Section 5 in the order given in Section 6
5. When a module is finished, update this log:
   - Move it from "NOT DONE" (❌) to "DONE" (✅) in Section 5
   - Add any new files created to the folder structure in Section 3
   - Note any schema changes (and update Section 4.1 + `er_diagram.mmd` if so)

---

# 8. QUICK REFERENCE — KEY NAMING CONVENTIONS

- UUID prefixes: `chr_` (character), `evt_` (event), `fac_` (faction), `uni_` (universe), `art_` (artifact), `sty_` (story), `root_` (root entity), `loc_` (location)
- `canon_status` allowed values: `canon`, `non_canon`, `alt_timeline`, `experimental`
- `story_mode` allowed values: `canon`, `non_canon`, `what_if`, `alt_timeline`, `rpg_sim`
- `edge_type` (relationships) allowed values: `friend`, `enemy`, `family`, `mentor`, `student`, `created`, `destroyed`, `owns`, `located_in`, `participated_in`
- `event_type` (events) common values: `birth`, `death`, `rebirth`, `war`, `other`
- `importance_score` range: 1-100 (Random Soldier ≈ 5, Raven ≈ 75, OM_X ≈ 100)
- `entity_type` (used in root_entity_links, event_participants, entity_tags, entity_notes, version_history): `'character'`, `'faction'`, `'location'`, `'event'`, `'universe'`, `'artifact'`, `'story'`

---

# END OF LOG — Total Progress: Phase 0 (Database Foundation) = 100% complete. Phase 1 onward = 0% complete.
