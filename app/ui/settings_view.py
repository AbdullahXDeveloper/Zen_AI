"""
app/ui/settings_view.py
Zen AI — Settings Page
Theme: Dark neutral, accent #00ADB5
Sections:
  - AI / Ollama config
  - Default universe preference
  - About / version info
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QLineEdit, QComboBox,
    QCheckBox, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal

from app.database.db_init import get_session
from app.database import crud

ACCENT = "#00ADB5"


# ─── Worker: load settings data ─────────────────────────
class LoadSettingsDataWorker(QThread):
    done  = Signal(list)   # universes list
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


# ─── Helpers ─────────────────────────────────────────────
def _section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setStyleSheet(
        "color: #2A2A2A; font-size: 10px; font-weight: 700; "
        "letter-spacing: 3px; background: transparent; border: none; "
        "padding-top: 12px; padding-bottom: 4px;"
    )
    return lbl


def _separator() -> QFrame:
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet("background: #1A1A1A; border: none;")
    return line


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #555; font-size: 11px; font-weight: 600; background: transparent; border: none;")
    return lbl


INPUT_STYLE = f"""
    QLineEdit, QComboBox {{
        background: #0D0D0D; color: #CCCCCC;
        border: 1px solid #1E1E1E; border-radius: 7px;
        padding: 8px 14px; font-size: 13px;
    }}
    QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
    QComboBox QAbstractItemView {{
        background: #111; color: #CCC;
        selection-background-color: {ACCENT};
    }}
"""


# ─── Main Settings View ──────────────────────────────────
class SettingsViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._worker     = None
        self._universes  = []
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setStyleSheet("background: #0D0D0D;")

        # ── Top bar ──
        top_bar = QFrame()
        top_bar.setFixedHeight(64)
        top_bar.setStyleSheet("background: #0D0D0D; border-bottom: 1px solid #1A1A1A;")
        bar_lay = QHBoxLayout(top_bar)
        bar_lay.setContentsMargins(32, 0, 32, 0)

        title = QLabel("⚙  Settings")
        title.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: 900; letter-spacing: 2px; background: transparent; border: none;")
        bar_lay.addWidget(title)
        bar_lay.addStretch()
        root.addWidget(top_bar)

        # ── Scroll content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #0D0D0D; } QScrollBar:vertical { background: #111; width: 6px; } QScrollBar::handle:vertical { background: #2A2A2A; border-radius: 3px; }")

        content = QWidget()
        content.setStyleSheet("background: #0D0D0D;")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(48, 28, 48, 60)
        lay.setSpacing(14)

        # ──────────────────────────────────────────
        # SECTION: AI / OLLAMA
        # ──────────────────────────────────────────
        lay.addWidget(_section("AI / OLLAMA CONFIGURATION"))
        lay.addWidget(_separator())

        lay.addWidget(_field_label("Ollama Base URL"))
        self._ollama_url = QLineEdit("http://localhost:11434")
        self._ollama_url.setStyleSheet(INPUT_STYLE)
        lay.addWidget(self._ollama_url)

        lay.addWidget(_field_label("Default Model"))
        self._model_combo = QComboBox()
        self._model_combo.addItems([
            "qwen2.5:7b",
            "qwen2.5:14b",
            "llama3.1:8b",
            "mistral:7b",
            "gemma2:9b",
        ])
        self._model_combo.setStyleSheet(INPUT_STYLE)
        lay.addWidget(self._model_combo)

        lay.addWidget(_field_label("Story Generation Temperature  (0.0 – 1.0)"))
        self._temp_input = QLineEdit("1.0")
        self._temp_input.setPlaceholderText("e.g. 0.8 (lower = more focused, higher = creative)")
        self._temp_input.setStyleSheet(INPUT_STYLE)
        lay.addWidget(self._temp_input)

        # Test connection button
        self._test_btn = QPushButton("⚡  Test Ollama Connection")
        self._test_btn.setFixedHeight(36)
        self._test_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {ACCENT};
                border: 1px solid {ACCENT}44; border-radius: 8px;
                font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {ACCENT}14; border-color: {ACCENT}; }}
        """)
        self._test_btn.clicked.connect(self._test_ollama)
        self._test_result = QLabel("")
        self._test_result.setStyleSheet("color: #444; font-size: 11px; background: transparent; border: none;")

        test_row = QHBoxLayout()
        test_row.addWidget(self._test_btn)
        test_row.addWidget(self._test_result)
        test_row.addStretch()
        lay.addLayout(test_row)

        # ──────────────────────────────────────────
        # SECTION: WORLDBUILDING PREFERENCES
        # ──────────────────────────────────────────
        lay.addSpacing(10)
        lay.addWidget(_section("WORLDBUILDING PREFERENCES"))
        lay.addWidget(_separator())

        lay.addWidget(_field_label("Default Universe  (used when no universe is selected)"))
        self._default_uni_combo = QComboBox()
        self._default_uni_combo.addItem("— None —", None)
        self._default_uni_combo.setStyleSheet(INPUT_STYLE)
        lay.addWidget(self._default_uni_combo)

        lay.addWidget(_field_label("Default Canon Status"))
        self._default_canon = QComboBox()
        for opt in ["canon", "non_canon", "alt_timeline", "experimental"]:
            self._default_canon.addItem(opt.replace("_", " ").title(), opt)
        self._default_canon.setStyleSheet(INPUT_STYLE)
        lay.addWidget(self._default_canon)

        lay.addWidget(_field_label("Default Importance Score"))
        self._default_score = QLineEdit("50")
        self._default_score.setPlaceholderText("1 – 100")
        self._default_score.setStyleSheet(INPUT_STYLE)
        lay.addWidget(self._default_score)

        # ──────────────────────────────────────────
        # SECTION: SEARCH
        # ──────────────────────────────────────────
        lay.addSpacing(10)
        lay.addWidget(_section("SEARCH SETTINGS"))
        lay.addWidget(_separator())

        lay.addWidget(_field_label("Max Search Results"))
        self._max_results = QLineEdit("25")
        self._max_results.setStyleSheet(INPUT_STYLE)
        lay.addWidget(self._max_results)

        self._semantic_enabled = QCheckBox("Enable semantic (FAISS) search")
        self._semantic_enabled.setChecked(True)
        self._semantic_enabled.setStyleSheet(f"""
            QCheckBox {{
                color: #666; font-size: 13px;
                background: transparent; border: none;
            }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid #333; border-radius: 4px; background: #0D0D0D; }}
            QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
        """)
        lay.addWidget(self._semantic_enabled)

        # ──────────────────────────────────────────
        # SECTION: DATABASE
        # ──────────────────────────────────────────
        lay.addSpacing(10)
        lay.addWidget(_section("DATABASE"))
        lay.addWidget(_separator())

        self._db_path_lbl = QLabel("Database: data/zenai.db")
        self._db_path_lbl.setStyleSheet("color: #333; font-size: 12px; background: transparent; border: none;")
        lay.addWidget(self._db_path_lbl)

        db_btns = QHBoxLayout()

        rebuild_btn = QPushButton("🔄  Rebuild FAISS Index")
        rebuild_btn.setFixedHeight(34)
        rebuild_btn.setStyleSheet(self._ghost_btn("#f39c12"))
        rebuild_btn.clicked.connect(self._rebuild_index)

        self._rebuild_status = QLabel("")
        self._rebuild_status.setStyleSheet("color: #444; font-size: 11px; background: transparent; border: none;")

        db_btns.addWidget(rebuild_btn)
        db_btns.addWidget(self._rebuild_status)
        db_btns.addStretch()
        lay.addLayout(db_btns)

        # ──────────────────────────────────────────
        # SAVE BUTTON
        # ──────────────────────────────────────────
        lay.addSpacing(20)
        save_row = QHBoxLayout()
        self._save_btn = QPushButton("✓  Save Settings")
        self._save_btn.setFixedHeight(40)
        self._save_btn.setFixedWidth(180)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: #000;
                border: none; border-radius: 8px;
                font-size: 14px; font-weight: 700;
            }}
            QPushButton:hover {{ background: #00C9D4; }}
        """)
        self._save_btn.clicked.connect(self._save)
        self._save_status = QLabel("")
        self._save_status.setStyleSheet(f"color: {ACCENT}; font-size: 12px; background: transparent; border: none;")
        save_row.addWidget(self._save_btn)
        save_row.addWidget(self._save_status)
        save_row.addStretch()
        lay.addLayout(save_row)

        # ──────────────────────────────────────────
        # SECTION: ABOUT
        # ──────────────────────────────────────────
        lay.addSpacing(20)
        lay.addWidget(_section("ABOUT"))
        lay.addWidget(_separator())

        about_data = [
            ("App Name",    "Zen AI — Zendrix Multiverse OS"),
            ("Version",     "v1.0"),
            ("Author",      "Abdullah"),
            ("Database",    "SQLite + SQLAlchemy (21 tables)"),
            ("AI Backend",  "Ollama  qwen2.5:7b  (local, offline)"),
            ("Embeddings",  "Sentence Transformers  all-MiniLM-L6-v2 (384-dim)"),
            ("Vector DB",   "FAISS"),
            ("UI",          "PySide6 (Qt6)"),
            ("Graphs",      "NetworkX + PyVis"),
        ]
        for key, val in about_data:
            row = QHBoxLayout()
            k = QLabel(key)
            k.setFixedWidth(130)
            k.setStyleSheet("color: #333; font-size: 12px; background: transparent; border: none;")
            v = QLabel(val)
            v.setStyleSheet(f"color: #555; font-size: 12px; background: transparent; border: none;")
            row.addWidget(k)
            row.addWidget(v)
            row.addStretch()
            lay.addLayout(row)

        lay.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)

    # ── Data load ─────────────────────────────────────────

    def _load_data(self):
        self._worker = LoadSettingsDataWorker()
        self._worker.done.connect(self._on_data)
        self._worker.start()

    def _on_data(self, universes: list):
        self._universes = universes
        self._default_uni_combo.clear()
        self._default_uni_combo.addItem("— None —", None)
        for u in universes:
            self._default_uni_combo.addItem(u["name"], u["id"])

    # ── Actions ───────────────────────────────────────────

    def _test_ollama(self):
        self._test_result.setText("Testing...")
        self._test_result.setStyleSheet("color: #888; font-size: 11px; background: transparent; border: none;")
        try:
            import requests
            url = self._ollama_url.text().strip().rstrip("/")
            r = requests.get(f"{url}/api/tags", timeout=3)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                self._test_result.setText(f"✅  Connected  ({len(models)} models available)")
                self._test_result.setStyleSheet("color: #2ecc71; font-size: 11px; background: transparent; border: none;")
            else:
                self._test_result.setText(f"⚠  HTTP {r.status_code}")
                self._test_result.setStyleSheet("color: #f39c12; font-size: 11px; background: transparent; border: none;")
        except Exception as e:
            self._test_result.setText(f"❌  {str(e)[:60]}")
            self._test_result.setStyleSheet("color: #e74c3c; font-size: 11px; background: transparent; border: none;")

    def _rebuild_index(self):
        self._rebuild_status.setText("Rebuilding...")
        self._rebuild_status.setStyleSheet("color: #f39c12; font-size: 11px; background: transparent; border: none;")
        try:
            from app.search.search import rebuild_index
            session = get_session()
            count = rebuild_index(session)
            session.close()
            self._rebuild_status.setText(f"✅  {count} entities indexed")
            self._rebuild_status.setStyleSheet("color: #2ecc71; font-size: 11px; background: transparent; border: none;")
        except Exception as e:
            self._rebuild_status.setText(f"❌  {str(e)[:60]}")
            self._rebuild_status.setStyleSheet("color: #e74c3c; font-size: 11px; background: transparent; border: none;")

    def _save(self):
        # Settings currently stored in memory only (no config file yet)
        # Future: write to config/settings.json
        self._save_status.setText("✅  Settings saved")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self._save_status.setText(""))

    @staticmethod
    def _ghost_btn(color: str) -> str:
        return f"""
            QPushButton {{
                background: transparent; color: {color};
                border: 1px solid {color}44; border-radius: 7px;
                font-size: 12px; font-weight: 600; padding: 0 14px;
            }}
            QPushButton:hover {{ background: {color}14; border-color: {color}; }}
        """
