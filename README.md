<div align="center">
  <img src="https://via.placeholder.com/150/00ADB5/FFFFFF?text=Zen+AI" alt="Zen AI Logo" width="120" height="120" />
  <h1>Zen AI — The Universal Worldbuilding Operating System</h1>
  <p><em>A desktop AI-powered worldbuilding operating system for managing and visualizing expansive fictional multiverses.</em></p>
</div>

---

## 🌌 Project Overview
**ZenAI** is an interactive, lore-aware operating system built to manage, expand, and visualize any fictional universe or multiverse. Whether you're building a novel, a tabletop RPG campaign, or a complex cosmic continuity (e.g., the Zendrix Multiverse), ZenAI serves as your **Second Brain**.

Rather than relying on scattered text documents, ZenAI stores the lore in a robust relational database, indexes it via semantic vector search (FAISS), and allows the creator to converse with an omniscient AI archivist powered by blazing-fast inference engines (e.g., Groq/Llama-3).

---

## 🚀 Features & Functions

### 1. Robust Relational Lore Database
- A structured schema that interlinks Characters, Factions, Locations, Artifacts, Events, and Stories.
- Global unique identifiers (`UUIDs`) and canonical tracking (canon, alternate timelines, non-canon).

### 2. Premium UI Shell (Glassmorphic OS)
- A state-of-the-art **desktop app** featuring a dark-mode, glassmorphic aesthetic.
- **Dashboard:** Live analytics of your created universes, character stats, and system status.
- **Cosmic View:** Interactive node-graph representations of universes, relationships, and timelines.

### 3. Lore-Aware AI Archivist
- Powered by fast inference (e.g., **Groq**), the AI answers queries in real-time by performing Retrieval-Augmented Generation (RAG).
- The AI acts as an omniscient guide that pulls actual context from your database to answer questions about specific characters, events, and lore.

### 4. Advanced Vector Search
- Semantic search capabilities using **Sentence Transformers**.
- Entities are embedded in a high-dimensional vector space, allowing the AI to instantly recall relevant context even from vague queries.

### 5. Bulk Data Import
- Rapidly ingest thousands of JSON-formatted data entries directly into the database, with automatic indexing for immediate AI recall.

---

## 🔮 Future Scope (In Development)

| Module | Planned Feature | Description |
|---|---|---|
| **Knowledge Graph** | Network Maps | Interactive mind-maps showing relationships between all characters and factions across universes. |
| **Document Ingestion** | Pipeline Extraction | Upload DOCX/PDF files, and the AI will automatically extract entities, powers, and events to populate the DB. |
| **Timeline Engine** | Chronometer Zoom | A visual chronometer allowing you to zoom from a macro timeline down to a specific event. |
| **Wiki Generator** | Auto-Documentation | Automatically generate HTML wiki pages for every entity in the database. |
| **Simulation Engine** | "What If" Scenarios | Run butterfly-effect simulations and let the AI predict the fallout of changed events. |

---

## 🛠️ Requirements & Setup

### Prerequisites
- **Python 3.10+**
- A **Groq API Key** (or supported AI provider)
- Windows / macOS / Linux

### 1. Clone the Repository
```bash
git clone <repository_url>
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
GROQ_API_KEY=your_api_key_here
```

### 5. Initialize the Database
```bash
python -m app.database.db_init
```

### 6. Run the Application
```bash
python main.py
```

---

## 🗃️ Bulk Import Data
If you have generated lore, format it as `bulk_data.json` and run:
```bash
python bulk_import.py
```

---

## 📄 License
MIT License.
