"""
app/ui/lore_upload_view.py
Zen AI — Lore Upload Page
Theme: Orange  #e67e22
- Upload DOCX / PDF / TXT files
- Paste raw text
- Shows extraction progress: chunks, candidates, entities found
- AI-powered 3-phase pipeline (uses app/lore/pipeline.py)
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QComboBox, QTextEdit,
    QFileDialog, QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal

from app.database.db_init import get_session
from app.database import crud

ACCENT = "#e67e22"
SUPPORTED_EXTS = [".docx", ".pdf", ".txt", ".md"]


# ─── Worker ─────────────────────────────────────────────
class IngestWorker(QThread):
    progress = Signal(str)   # status message
    done     = Signal(dict)  # ingestion result dict
    error    = Signal(str)

    def __init__(self, source: str, universe_id: int = None, is_file: bool = True):
        super().__init__()
        self.source      = source   # file path or raw text
        self.universe_id = universe_id
        self.is_file     = is_file

    def run(self):
        try:
            from app.lore.pipeline import ingest_document, ingest_text
            session = get_session()

            if self.is_file:
                self.progress.emit(f"Reading file: {os.path.basename(self.source)}...")
                result = ingest_document(session, self.source, universe_id=self.universe_id)
            else:
                self.progress.emit("Processing pasted text...")
                result = ingest_text(session, self.source, universe_id=self.universe_id)

            session.close()
            self.done.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class LoadUniversesForUploadWorker(QThread):
    done  = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            session = get_session()
            unis = crud.list_universes(session)
            result = [{"id": u.id, "name": u.name} for u in unis]
            session.close()
            self.done.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ─── Main Upload View ────────────────────────────────────
class LoreUploadViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._worker     = None
        self._uni_worker = None
        self._universes  = []
        self._last_result = None
        self._setup_ui()
        self._load_universes()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.setStyleSheet("background: #0D0D0D;")

        # ── Top bar ──
        top_bar = QFrame()
        top_bar.setFixedHeight(64)
        top_bar.setStyleSheet("background: #0D0D0D; border-bottom: 1px solid #1A1A1A;")
        bar_lay = QHBoxLayout(top_bar)
        bar_lay.setContentsMargins(32, 0, 32, 0)

        title = QLabel("⬆  Lore Upload")
        title.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: 900; letter-spacing: 2px; background: transparent; border: none;")
        self._status_lbl = QLabel("AI-powered lore extraction from DOCX, PDF, TXT, or pasted text")
        self._status_lbl.setStyleSheet("color: #333; font-size: 11px; background: transparent; border: none;")
        bar_lay.addWidget(title)
        bar_lay.addStretch()
        bar_lay.addWidget(self._status_lbl)
        lay.addWidget(top_bar)

        # ── Scrollable content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #0D0D0D; } QScrollBar:vertical { background: #111; width: 6px; } QScrollBar::handle:vertical { background: #2A2A2A; border-radius: 3px; }")
        content = QWidget()
        content.setStyleSheet("background: #0D0D0D;")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(48, 32, 48, 48)
        c_lay.setSpacing(24)

        # ── Universe selector ──
        uni_row = QHBoxLayout()
        uni_lbl = QLabel("Target Universe:")
        uni_lbl.setStyleSheet(f"color: #888; font-size: 13px; font-weight: 600; background: transparent; border: none;")
        self._uni_combo = QComboBox()
        self._uni_combo.addItem("— No specific Universe —", None)
        self._uni_combo.setFixedWidth(260)
        self._uni_combo.setStyleSheet(f"""
            QComboBox {{
                background: #111; color: #CCC;
                border: 1px solid #222; border-radius: 7px;
                padding: 0 14px; font-size: 13px; height: 36px;
            }}
            QComboBox:focus {{ border-color: {ACCENT}; }}
            QComboBox QAbstractItemView {{
                background: #111; color: #CCC;
                selection-background-color: {ACCENT};
            }}
        """)
        uni_row.addWidget(uni_lbl)
        uni_row.addWidget(self._uni_combo)
        uni_row.addStretch()
        c_lay.addLayout(uni_row)

        # ── File Drop Zone ──
        drop_zone = QFrame()
        drop_zone.setFixedHeight(160)
        drop_zone.setStyleSheet(f"""
            QFrame {{
                background: #0A0A0A;
                border: 2px dashed #2A2A2A;
                border-radius: 14px;
            }}
            QFrame:hover {{
                border-color: {ACCENT};
                background: #0D0A06;
            }}
        """)
        dz_lay = QVBoxLayout(drop_zone)
        dz_lay.setAlignment(Qt.AlignCenter)
        dz_lay.setSpacing(10)

        drop_icon = QLabel("📁")
        drop_icon.setStyleSheet("font-size: 40px; background: transparent; border: none;")
        drop_icon.setAlignment(Qt.AlignCenter)
        dz_lay.addWidget(drop_icon)

        drop_hint = QLabel("File upload ke liye button dabain")
        drop_hint.setStyleSheet("color: #333; font-size: 13px; background: transparent; border: none;")
        drop_hint.setAlignment(Qt.AlignCenter)
        dz_lay.addWidget(drop_hint)

        ext_hint = QLabel("Supported: .docx  .pdf  .txt  .md")
        ext_hint.setStyleSheet("color: #222; font-size: 11px; background: transparent; border: none;")
        ext_hint.setAlignment(Qt.AlignCenter)
        dz_lay.addWidget(ext_hint)

        self._upload_btn = QPushButton("📂  Choose File")
        self._upload_btn.setFixedSize(160, 36)
        self._upload_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: #000;
                border: none; border-radius: 8px;
                font-size: 13px; font-weight: 700;
            }}
            QPushButton:hover {{ background: #f39c12; }}
            QPushButton:disabled {{ background: #2A1500; color: #555; }}
        """)
        self._upload_btn.clicked.connect(self._pick_file)
        dz_lay.addWidget(self._upload_btn, alignment=Qt.AlignCenter)
        c_lay.addWidget(drop_zone)

        # ── Divider ──
        div = QLabel("— YA TEXT PASTE KAREIN —")
        div.setAlignment(Qt.AlignCenter)
        div.setStyleSheet("color: #1E1E1E; font-size: 11px; font-weight: 700; letter-spacing: 2px; background: transparent; border: none;")
        c_lay.addWidget(div)

        # ── Paste Text Zone ──
        self._text_input = QTextEdit()
        self._text_input.setPlaceholderText(
            "Apni lore / story text yahan paste karein...\n\n"
            "AI automatically characters, factions, locations, events, aur artifacts extract karega.\n\n"
            "Minimum 100 characters required."
        )
        self._text_input.setFixedHeight(180)
        self._text_input.setStyleSheet(f"""
            QTextEdit {{
                background: #0A0A0A; color: #CCC;
                border: 1px solid #1E1E1E; border-radius: 10px;
                padding: 14px; font-size: 13px;
            }}
            QTextEdit:focus {{ border-color: {ACCENT}; }}
        """)
        c_lay.addWidget(self._text_input)

        self._process_text_btn = QPushButton("✦  Process Text")
        self._process_text_btn.setFixedHeight(40)
        self._process_text_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {ACCENT};
                border: 1px solid {ACCENT}44; border-radius: 8px;
                font-size: 13px; font-weight: 700;
            }}
            QPushButton:hover {{ background: {ACCENT}14; border-color: {ACCENT}; }}
            QPushButton:disabled {{ color: #333; border-color: #1A1A1A; }}
        """)
        self._process_text_btn.clicked.connect(self._process_text)
        c_lay.addWidget(self._process_text_btn)

        # ── Progress + Status ──
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)   # indeterminate
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{ background: #111; border: none; border-radius: 2px; }}
            QProgressBar::chunk {{ background: {ACCENT}; border-radius: 2px; }}
        """)
        self._progress_bar.hide()
        c_lay.addWidget(self._progress_bar)

        self._log_box = QTextEdit()
        self._log_box.setReadOnly(True)
        self._log_box.setFixedHeight(200)
        self._log_box.setStyleSheet(f"""
            QTextEdit {{
                background: #060606; color: #2ecc71;
                border: 1px solid #111; border-radius: 8px;
                padding: 12px; font-size: 12px; font-family: monospace;
            }}
        """)
        self._log_box.setPlaceholderText("[Zen AI Extractor] Ready...")
        c_lay.addWidget(self._log_box)

        c_lay.addStretch()
        scroll.setWidget(content)
        lay.addWidget(scroll)

    # ── Universe load ─────────────────────────────────────

    def _load_universes(self):
        self._uni_worker = LoadUniversesForUploadWorker()
        self._uni_worker.done.connect(self._on_universes_loaded)
        self._uni_worker.start()

    def _on_universes_loaded(self, universes: list):
        self._universes = universes
        self._uni_combo.clear()
        self._uni_combo.addItem("— No specific Universe —", None)
        for u in universes:
            self._uni_combo.addItem(u["name"], u["id"])

    # ── File Pick ─────────────────────────────────────────

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Lore File Select Karein", "",
            "Supported Files (*.docx *.pdf *.txt *.md);;All Files (*)"
        )
        if not path:
            return
        self._log(f"[File] {os.path.basename(path)} selected")
        self._start_ingest(path, is_file=True)

    # ── Text Process ──────────────────────────────────────

    def _process_text(self):
        text = self._text_input.toPlainText().strip()
        if len(text) < 100:
            self._log("[Error] Minimum 100 characters required")
            return
        self._log(f"[Text] {len(text)} chars — processing...")
        self._start_ingest(text, is_file=False)

    # ── Ingest ────────────────────────────────────────────

    def _start_ingest(self, source: str, is_file: bool):
        self._upload_btn.setEnabled(False)
        self._process_text_btn.setEnabled(False)
        self._progress_bar.show()
        universe_id = self._uni_combo.currentData()

        self._worker = IngestWorker(source, universe_id=universe_id, is_file=is_file)
        self._worker.progress.connect(self._log)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, result: dict):
        self._progress_bar.hide()
        self._upload_btn.setEnabled(True)
        self._process_text_btn.setEnabled(True)
        self._last_result = result

        m = result.get("merged_result", {})
        self._log("─" * 50)
        self._log(f"[Done] Chunks: {result.get('chunks_processed', 0)}/{result.get('chunks_total', 0)} processed")
        self._log(f"  👤 Characters : {len(m.get('characters', []))}")
        self._log(f"  ⚔  Factions   : {len(m.get('factions', []))}")
        self._log(f"  📍 Locations  : {len(m.get('locations', []))}")
        self._log(f"  📅 Events     : {len(m.get('events', []))}")
        self._log(f"  💎 Artifacts  : {len(m.get('artifacts', []))}")
        self._log(f"  🔗 Relationships: {len(m.get('relationships', []))}")
        self._log("─" * 50)
        self._log("[Zen AI] Extraction complete. Results reviewed aur approved ho jayein ge.")

    def _on_error(self, msg: str):
        self._progress_bar.hide()
        self._upload_btn.setEnabled(True)
        self._process_text_btn.setEnabled(True)
        self._log(f"[Error] {msg}")

    def _log(self, msg: str):
        self._log_box.append(msg)
        self._log_box.verticalScrollBar().setValue(
            self._log_box.verticalScrollBar().maximum()
        )
