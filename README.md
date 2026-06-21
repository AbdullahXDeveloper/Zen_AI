<div align="center">
  <img src="https://via.placeholder.com/150/00ADB5/FFFFFF?text=Zen+AI" alt="Zen AI Logo" width="120" height="120" />
  <h1>Zen AI — The Cosmic Archive of Zendrix</h1>
  <p><em>A desktop AI-powered worldbuilding operating system for the Zendrix multiverse paracosm.</em></p>
</div>

---

## 🌌 Project Overview
**ZenAI** is not a simple chatbot. It is a **Second Brain** and an interactive, lore-aware operating system built to manage, expand, and visualize an entire fictional multiverse (Zendrix). 

Rather than relying on scattered text documents, ZenAI stores the lore in a robust relational database, indexes it via semantic vector search (FAISS), and allows the creator to converse with **Zen**, an omniscient AI archivist powered by blazing-fast inference engines (Groq/Llama-3).

### What is Zendrix?
- **Zendrix Tree:** The master cosmic structure holding all realities.
- **Fruits (Universes):** Individual realities hanging from the Tree, each with their own characters, factions, and histories.
- **Root Entities:** Unique, multiversal beings (e.g., OM_X, K, _LA) that exist across all universes and are never duplicated.

---

## 🚀 Features & Functions (Current Capabilities)

### 1. Robust Relational Lore Database
- A **21-table SQLite schema** that interlinks Characters, Factions, Locations, Artifacts, Events, and Stories.
- Global unique identifiers (`UUIDs`) and canonical tracking (`canon`, `alt_timeline`, `non_canon`).

### 2. Premium UI Shell (Glassmorphic OS)
- A state-of-the-art **PySide6 desktop app** featuring a dark-mode, glassmorphic aesthetic.
- **Dashboard:** Live analytics of the multiverse (universe counts, character cosmic weight bars, glowing system statuses).
- **Cosmic View:** Interactive node-graph representations of universes and timelines.

### 3. Lore-Aware AI Archivist (Zen)
- Powered by **Groq**, Zen answers queries in real-time by performing Retrieval-Augmented Generation (RAG).
- Zen acts as a poetic, omniscient guide that pulls actual context from the database to answer questions about specific characters, events, and lore.

### 4. Advanced Vector Search (FAISS)
- Semantic search capabilities using **Sentence Transformers** (`all-MiniLM-L6-v2`).
- Entities are embedded in a high-dimensional vector space, allowing the AI to instantly recall relevant context even from vague queries.

### 5. Bulk Data Import
- `bulk_import.py` allows creators to rapidly ingest thousands of JSON-formatted data entries directly into the SQLite database and rebuilds the FAISS index automatically.

---

## 🔮 Future Scope (In Development)

| Module | Planned Feature | Description |
|---|---|---|
| **Knowledge Graph** | NetworkX + PyVis | Interactive mind-maps showing relationships between all characters and factions across universes. |
| **Document Ingestion** | Pipeline Extraction | Upload DOCX/PDF files, and the AI will automatically extract entities, powers, and events to populate the DB. |
| **Timeline Engine** | Multiverse Zoom | A visual chronometer allowing the creator to zoom from a multiverse epoch down to a specific character's birth. |
| **Wiki Generator** | Auto-Documentation | Automatically generate Wikipedia-style HTML pages for every entity in the database. |
| **Simulation Engine** | "What If" Scenarios | Run butterfly-effect simulations (e.g., "What if Character A killed Character B?") and let the AI predict the cosmic fallout. |

---

## 🛠️ Requirements & Setup

### Prerequisites
- **Python 3.10+**
- A **Groq API Key** (for fast AI inference)
- Windows / macOS / Linux

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/ZenAI.git
cd ZenAI
```

### 2. Set Up Virtual Environment
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Create a `config/.env` file in the project root:
```env
GROQ_API_KEY=gsk_your_api_key_here
```

### 5. Initialize the Database
```bash
python -m app.database.db_init
```
*(This automatically creates the `data/zenai.db` SQLite file and seeds the Root Entities).*

### 6. Run the Application
```bash
python main.py
```
*(On first launch, the app will download the embedding model and build the initial FAISS index).*

---

## 🗃️ Bulk Import Data
If you have generated lore using ChatGPT or Claude, format it as `bulk_data.json` and run:
```bash
python bulk_import.py
```
This script will safely ingest the data, assign UUIDs, and **automatically rebuild the FAISS index** so the AI can immediately recall the new lore.

---

## 📄 License
MIT License. Built for the Zendrix Cosmic Archive.
