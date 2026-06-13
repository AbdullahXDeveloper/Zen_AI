"""
app.lore package — Document Ingestion Engine (Module 2)

3-Phase Pipeline:
1. Regex/Pattern Extraction (free, local) — candidates.py
2. Claude Extraction (structured JSON) — extractor.py
3. Human Review (Approve/Reject/Edit) → CRUD layer — review.py

File readers: DOCX, PDF, TXT/MD — readers.py
Orchestration: pipeline.py
"""
