"""
app/ui/search_view.py
Zen AI — Search Page (Module 6 Frontend)
Theme: White/Silver  #EEEEEE
- Hybrid search: exact + FAISS semantic
- Entity type filter
- Result cards with type badge + match type
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QLineEdit, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer

from app.database.db_init import get_session
from app.search.search import search as zen_search

ACCENT = "#EEEEEE"
ENTITY_COLORS = {
    "character": "#9b59b6",
    "faction":   "#f39c12",
    "location":  "#2ecc71",
    "event":     "#e74c3c",
    "artifact":  "#00BCD4",
    "story":     "#8e44ad",
    "universe":  "#00ADB5",
}
ENTITY_ICONS = {
    "character": "👤", "faction": "⚔", "location": "📍",
    "event": "📅", "artifact": "💎", "story": "📖", "universe": "🌐",
}


# ─── Worker ─────────────────────────────────────────────
class SearchWorker(QThread):
    done  = Signal(list)
    error = Signal(str)

    def __init__(self, query: str, entity_type: str = None, top_k: int = 20):
        super().__init__()
        self.query       = query
        self.entity_type = entity_type
        self.top_k       = top_k

    def run(self):
        try:
            session = get_session()
            results = zen_search(
                session,
                self.query,
                entity_type=self.entity_type,
                top_k=self.top_k,
            )
            session.close()
            self.done.emit(results)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


# ─── Result Card ────────────────────────────────────────
class ResultCard(QFrame):
    def __init__(self, data: dict, rank: int):
        super().__init__()
        etype = data.get("entity_type", "unknown")
        color = ENTITY_COLORS.get(etype, "#555555")
        icon  = ENTITY_ICONS.get(etype, "❓")
        match_type = data.get("match_type", "semantic")
        score      = data.get("score", 0.0)

        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(f"""
            QFrame {{
                background: #111111; border: 1px solid #1E1E1E;
                border-left: 4px solid {color}; border-radius: 8px;
            }}
            QFrame:hover {{ background: #161616; border-left: 4px solid {color}; }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(16)

        # Rank number
        rank_lbl = QLabel(f"#{rank}")
        rank_lbl.setFixedWidth(32)
        rank_lbl.setStyleSheet(f"color: {color}44; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        rank_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(rank_lbl)

        # Entity icon + name
        info = QVBoxLayout()
        info.setSpacing(2)

        name_row = QHBoxLayout()
        icon_lbl = QLabel(f"{icon}  {data.get('name', '—')}")
        icon_lbl.setStyleSheet("color: #EEEEEE; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        name_row.addWidget(icon_lbl)
        name_row.addStretch()
        info.addLayout(name_row)

        meta_row = QHBoxLayout()
        type_lbl = QLabel(etype.upper())
        type_lbl.setStyleSheet(
            f"color: {color}; font-size: 9px; font-weight: 700; "
            f"background: {color}18; border: 1px solid {color}44; "
            "border-radius: 3px; padding: 1px 7px;"
        )
        match_lbl = QLabel(
            "🎯 Exact Match" if match_type == "exact" else f"🧠 Semantic  {score:.2f}"
        )
        match_lbl.setStyleSheet(
            f"color: {'#2ecc71' if match_type == 'exact' else '#444'}; "
            "font-size: 10px; background: transparent; border: none;"
        )
        meta_row.addWidget(type_lbl)
        meta_row.addSpacing(10)
        meta_row.addWidget(match_lbl)
        meta_row.addStretch()
        info.addLayout(meta_row)

        lay.addLayout(info)


# ─── Main Search View ────────────────────────────────────
class SearchViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._workers = []
        self._results = []
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(400)
        self._debounce.timeout.connect(self._run_search)
        self._setup_ui()

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
        bar_lay.setSpacing(12)

        title = QLabel("🔍  Search")
        title.setStyleSheet("color: #EEEEEE; font-size: 20px; font-weight: 900; letter-spacing: 2px; background: transparent; border: none;")
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color: #333; font-size: 11px; background: transparent; border: none;")
        bar_lay.addWidget(title)
        bar_lay.addStretch()
        bar_lay.addWidget(self._count_lbl)
        lay.addWidget(top_bar)

        # ── Search bar ──
        search_bar = QFrame()
        search_bar.setStyleSheet("background: #0A0A0A; border-bottom: 1px solid #141414;")
        s_lay = QHBoxLayout(search_bar)
        s_lay.setContentsMargins(32, 14, 32, 14)
        s_lay.setSpacing(12)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍  Kuch bhi search karein... (character, faction, event, story, artifact)")
        self._search_input.setFixedHeight(40)
        self._search_input.setStyleSheet("""
            QLineEdit {
                background: #111; color: #EEE;
                border: 1px solid #2A2A2A; border-radius: 8px;
                padding: 0 16px; font-size: 14px;
            }
            QLineEdit:focus { border-color: #EEEEEE; }
        """)
        self._search_input.textChanged.connect(self._on_text_changed)
        self._search_input.returnPressed.connect(self._run_search)

        combo_style = """
            QComboBox {
                background: #111; color: #888;
                border: 1px solid #222; border-radius: 7px;
                padding: 0 12px; font-size: 12px;
                min-width: 140px; height: 40px;
            }
            QComboBox QAbstractItemView { background: #111; color: #CCC; selection-background-color: #EEE; }
        """
        self._type_combo = QComboBox()
        self._type_combo.addItem("All Types", None)
        for et in ["character", "faction", "location", "event", "artifact", "story"]:
            icon = ENTITY_ICONS.get(et, "")
            self._type_combo.addItem(f"{icon} {et.title()}", et)
        self._type_combo.setStyleSheet(combo_style)
        self._type_combo.currentIndexChanged.connect(self._on_filter_changed)

        self._search_btn = QPushButton("Search")
        self._search_btn.setFixedHeight(40)
        self._search_btn.setFixedWidth(90)
        self._search_btn.setStyleSheet("""
            QPushButton {
                background: #EEEEEE; color: #000;
                border: none; border-radius: 8px;
                font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background: #FFFFFF; }
        """)
        self._search_btn.clicked.connect(self._run_search)

        s_lay.addWidget(self._search_input)
        s_lay.addWidget(self._type_combo)
        s_lay.addWidget(self._search_btn)
        lay.addWidget(search_bar)

        # ── Results area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: #0D0D0D; }
            QScrollBar:vertical { background: #111; width: 6px; }
            QScrollBar::handle:vertical { background: #2A2A2A; border-radius: 3px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #EEE; }
        """)
        self._results_widget = QWidget()
        self._results_widget.setStyleSheet("background: #0D0D0D;")
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setContentsMargins(32, 24, 32, 32)
        self._results_layout.setSpacing(10)
        self._results_layout.setAlignment(Qt.AlignTop)
        self._scroll.setWidget(self._results_widget)
        lay.addWidget(self._scroll)

        # Placeholder on load
        self._show_placeholder("Kuch type karein...")

    def _on_text_changed(self, text: str):
        if len(text) >= 2:
            self._debounce.start()
        elif len(text) == 0:
            self._debounce.stop()
            self._show_placeholder("Kuch type karein...")

    def _on_filter_changed(self):
        query = self._search_input.text().strip()
        if len(query) >= 2:
            self._run_search()

    def _run_search(self):
        query = self._search_input.text().strip()
        if not query:
            return

        self._count_lbl.setText("Searching...")
        self._clear_results()
        entity_type = self._type_combo.currentData()

        # Clean up finished workers just in case
        self._workers = [w for w in self._workers if w.isRunning()]

        worker = SearchWorker(query, entity_type, top_k=25)
        worker.done.connect(lambda res, w=worker: self._handle_worker_done(res, w))
        worker.error.connect(lambda err, w=worker: self._handle_worker_error(err, w))
        self._workers.append(worker)
        worker.start()

    def _handle_worker_done(self, results, worker):
        if worker in self._workers:
            self._workers.remove(worker)
        # Only update UI if this is the most recently created worker
        if not self._workers:
            self._on_results(results)

    def _handle_worker_error(self, err, worker):
        if worker in self._workers:
            self._workers.remove(worker)
        if not self._workers:
            self._on_error(err)

    def _on_results(self, results: list):
        self._results = results
        self._clear_results()

        count = len(results)
        self._count_lbl.setText(f"{count} result{'s' if count != 1 else ''}")

        if not results:
            self._show_placeholder("Koi result nahi mila.\n\nDosri query try karein.")
            return

        for i, r in enumerate(results):
            card = ResultCard(r, i + 1)
            self._results_layout.addWidget(card)
        self._results_layout.addStretch()

    def _on_error(self, msg: str):
        self._count_lbl.setText(f"Error: {msg}")

    def _clear_results(self):
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_placeholder(self, msg: str):
        self._clear_results()
        lbl = QLabel(msg)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #1E1E1E; font-size: 20px; font-weight: 600; padding: 80px; background: transparent; border: none;")
        self._results_layout.addWidget(lbl)
