"""
app/ui/settings_view.py
Zen AI — Settings Page  v2
Theme: Dark neutral, accent #00ADB5

Sections:
  1. AI MODEL PROVIDER  (Ollama local / OpenAI API / Google Gemini / Anthropic Claude)
  2. OLLAMA CONFIG
  3. WINDOW / DISPLAY  (resolution manual set)
  4. WORLDBUILDING PREFERENCES
  5. SEARCH SETTINGS
  6. DATABASE
  7. ABOUT
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QLineEdit, QComboBox,
    QCheckBox, QSizePolicy, QStackedWidget, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QScreen

from app.database.db_init import get_session
from app.database import crud
from config.app_settings import get_app_settings
from app.ai.claude_client import rebuild_client

ACCENT = "#00ADB5"

# ─── AI Providers ────────────────────────────────────────
PROVIDERS = [
    {
        "id":    "ollama",
        "label": "🦙  Ollama  (Local, Offline)",
        "needs_key": False,
        "needs_url": True,
        "models": ["qwen2.5:7b", "qwen2.5:14b", "llama3.1:8b",
                   "mistral:7b", "gemma2:9b", "phi3:3.8b"],
        "api_label": None,
    },
    {
        "id":    "openai",
        "label": "🤖  OpenAI  (GPT-4o, GPT-4, GPT-3.5)",
        "needs_key": True,
        "needs_url": False,
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        "api_label": "OpenAI API Key",
    },
    {
        "id":    "gemini",
        "label": "✦  Google Gemini  (Gemini 1.5 Pro, Flash)",
        "needs_key": True,
        "needs_url": False,
        "models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-pro"],
        "api_label": "Gemini API Key  (aistudio.google.com)",
    },
    {
        "id":    "anthropic",
        "label": "🧠  Anthropic Claude  (Claude 3.5 Sonnet)",
        "needs_key": True,
        "needs_url": False,
        "models": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307", "claude-3-opus-20240229"],
        "api_label": "Anthropic API Key",
    },
    {
        "id":    "custom",
        "label": "⚙  Custom OpenAI-Compatible API",
        "needs_key": True,
        "needs_url": True,
        "models": [],
        "api_label": "API Key",
    },
]

RESOLUTIONS = [
    ("1280 × 720   (HD)",          1280, 720),
    ("1366 × 768   (Laptop)",      1366, 768),
    ("1440 × 900   (MacBook)",     1440, 900),
    ("1600 × 900",                 1600, 900),
    ("1920 × 1080  (Full HD)",     1920, 1080),
    ("2560 × 1440  (2K / QHD)",   2560, 1440),
    ("3840 × 2160  (4K UHD)",     3840, 2160),
    ("Custom",                     None, None),
]


# ─── Worker ─────────────────────────────────────────────
class LoadSettingsDataWorker(QThread):
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


# ─── Style helpers ───────────────────────────────────────
def _section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setStyleSheet(
        "color: #2A2A2A; font-size: 10px; font-weight: 700; "
        "letter-spacing: 3px; background: transparent; border: none; "
        "padding-top: 14px; padding-bottom: 4px;"
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

PASSWORD_STYLE = f"""
    QLineEdit {{
        background: #0D0D0D; color: #CCCCCC;
        border: 1px solid #1E1E1E; border-radius: 7px;
        padding: 8px 14px; font-size: 13px;
        letter-spacing: 1px;
    }}
    QLineEdit:focus {{ border-color: {ACCENT}; }}
"""


# ─── Main Settings View ──────────────────────────────────
class SettingsViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._worker    = None
        self._universes = []
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

        # ── Scroll area ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: #0D0D0D; } "
            "QScrollBar:vertical { background: #111; width: 6px; } "
            "QScrollBar::handle:vertical { background: #2A2A2A; border-radius: 3px; }"
        )

        content = QWidget()
        content.setStyleSheet("background: #0D0D0D;")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(48, 20, 48, 60)
        lay.setSpacing(10)

        # ══════════════════════════════════════════
        # SECTION 1 — AI MODEL PROVIDER
        # ══════════════════════════════════════════
        lay.addWidget(_section("AI MODEL PROVIDER"))
        lay.addWidget(_separator())

        lay.addWidget(_field_label("Active Provider"))
        self._provider_combo = QComboBox()
        for p in PROVIDERS:
            self._provider_combo.addItem(p["label"], p["id"])
        self._provider_combo.setStyleSheet(INPUT_STYLE)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        lay.addWidget(self._provider_combo)

        lay.addWidget(_field_label("Model"))
        self._model_combo = QComboBox()
        self._model_combo.setStyleSheet(INPUT_STYLE)
        self._model_combo.setEditable(True)
        self._model_combo.setInsertPolicy(QComboBox.NoInsert)
        lay.addWidget(self._model_combo)

        # API Key row (shown/hidden based on provider)
        self._api_key_frame = QFrame()
        self._api_key_frame.setStyleSheet("background: transparent; border: none;")
        ak_lay = QVBoxLayout(self._api_key_frame)
        ak_lay.setContentsMargins(0, 0, 0, 0)
        ak_lay.setSpacing(6)

        self._api_key_label = _field_label("API Key")
        self._api_key_input = QLineEdit()
        self._api_key_input.setEchoMode(QLineEdit.Password)
        self._api_key_input.setPlaceholderText("sk-... / AIza... — locally stored only")
        self._api_key_input.setStyleSheet(PASSWORD_STYLE)

        # Show/hide key toggle
        show_row = QHBoxLayout()
        self._show_key_btn = QPushButton("👁  Show")
        self._show_key_btn.setFixedHeight(28)
        self._show_key_btn.setCheckable(True)
        self._show_key_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: #444; border: 1px solid #1E1E1E; border-radius: 5px; font-size: 11px; padding: 0 12px; }}"
            f"QPushButton:checked {{ color: {ACCENT}; border-color: {ACCENT}44; }}"
        )
        self._show_key_btn.toggled.connect(self._toggle_key_vis)
        show_row.addWidget(self._api_key_input)
        show_row.addWidget(self._show_key_btn)

        ak_lay.addWidget(self._api_key_label)
        ak_lay.addLayout(show_row)
        lay.addWidget(self._api_key_frame)

        # Ollama-specific URL section
        self._ollama_frame = QFrame()
        self._ollama_frame.setStyleSheet("background: transparent; border: none;")
        of_lay = QVBoxLayout(self._ollama_frame)
        of_lay.setContentsMargins(0, 0, 0, 0)
        of_lay.setSpacing(6)

        of_lay.addWidget(_field_label("Ollama Base URL"))
        self._ollama_url = QLineEdit("http://localhost:11434")
        self._ollama_url.setStyleSheet(INPUT_STYLE)
        of_lay.addWidget(self._ollama_url)

        # Test connection
        test_row = QHBoxLayout()
        self._test_btn = QPushButton("⚡  Test Connection")
        self._test_btn.setFixedHeight(34)
        self._test_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {ACCENT}; border: 1px solid {ACCENT}44; border-radius: 8px; font-size: 12px; font-weight: 600; padding: 0 14px; }}"
            f"QPushButton:hover {{ background: {ACCENT}14; border-color: {ACCENT}; }}"
        )
        self._test_btn.clicked.connect(self._test_connection)
        self._test_result = QLabel("")
        self._test_result.setStyleSheet("color: #444; font-size: 11px; background: transparent; border: none;")
        test_row.addWidget(self._test_btn)
        test_row.addWidget(self._test_result)
        test_row.addStretch()
        of_lay.addLayout(test_row)
        lay.addWidget(self._ollama_frame)

        lay.addWidget(_field_label("Temperature  (0.0 – 1.0, higher = more creative)"))
        self._temp_input = QLineEdit("1.0")
        self._temp_input.setPlaceholderText("e.g. 0.8")
        self._temp_input.setStyleSheet(INPUT_STYLE)
        lay.addWidget(self._temp_input)

        # API key note
        self._key_note = QLabel("⚠  API key locally stored in memory only — not saved to disk in this version.")
        self._key_note.setStyleSheet("color: #2A2A2A; font-size: 10px; background: transparent; border: none;")
        self._key_note.setWordWrap(True)
        lay.addWidget(self._key_note)

        # NOTE: restore from saved settings is called after all widgets built
        # see _restore_ui_from_settings() called from _load_data()

        # ══════════════════════════════════════════
        # SECTION 2 — WINDOW / DISPLAY
        # ══════════════════════════════════════════
        lay.addWidget(_section("WINDOW / DISPLAY"))
        lay.addWidget(_separator())

        lay.addWidget(_field_label("Window Resolution  (resize on Save)"))
        res_row = QHBoxLayout()
        self._res_combo = QComboBox()
        for label, w, h in RESOLUTIONS:
            self._res_combo.addItem(label, (w, h))
        self._res_combo.setCurrentIndex(4)   # default: 1920×1080
        self._res_combo.setStyleSheet(INPUT_STYLE)
        self._res_combo.currentIndexChanged.connect(self._on_res_changed)
        res_row.addWidget(self._res_combo, 1)

        self._res_apply_btn = QPushButton("↔  Apply Now")
        self._res_apply_btn.setFixedHeight(34)
        self._res_apply_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {ACCENT}; border: 1px solid {ACCENT}44; border-radius: 7px; font-size: 12px; font-weight: 600; padding: 0 14px; }}"
            f"QPushButton:hover {{ background: {ACCENT}14; border-color: {ACCENT}; }}"
        )
        self._res_apply_btn.clicked.connect(self._apply_resolution)
        res_row.addWidget(self._res_apply_btn)
        lay.addLayout(res_row)

        # Custom resolution row
        self._custom_res_frame = QFrame()
        self._custom_res_frame.setStyleSheet("background: transparent; border: none;")
        cr_lay = QHBoxLayout(self._custom_res_frame)
        cr_lay.setContentsMargins(0, 0, 0, 0)
        cr_lay.setSpacing(8)

        cr_lay.addWidget(_field_label("Width:"))
        self._custom_w = QLineEdit("1280")
        self._custom_w.setFixedWidth(100)
        self._custom_w.setStyleSheet(INPUT_STYLE)
        cr_lay.addWidget(self._custom_w)

        cr_lay.addWidget(_field_label("Height:"))
        self._custom_h = QLineEdit("720")
        self._custom_h.setFixedWidth(100)
        self._custom_h.setStyleSheet(INPUT_STYLE)
        cr_lay.addWidget(self._custom_h)
        cr_lay.addStretch()
        self._custom_res_frame.hide()
        lay.addWidget(self._custom_res_frame)

        self._res_note = QLabel("")
        self._res_note.setStyleSheet("color: #2A2A2A; font-size: 10px; background: transparent; border: none;")
        lay.addWidget(self._res_note)
        self._update_res_note()

        # ══════════════════════════════════════════
        # SECTION 3 — WORLDBUILDING PREFERENCES
        # ══════════════════════════════════════════
        lay.addWidget(_section("WORLDBUILDING PREFERENCES"))
        lay.addWidget(_separator())

        lay.addWidget(_field_label("Default Universe"))
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

        # ══════════════════════════════════════════
        # SECTION 4 — SEARCH SETTINGS
        # ══════════════════════════════════════════
        lay.addWidget(_section("SEARCH SETTINGS"))
        lay.addWidget(_separator())

        lay.addWidget(_field_label("Max Search Results"))
        self._max_results = QLineEdit("25")
        self._max_results.setStyleSheet(INPUT_STYLE)
        lay.addWidget(self._max_results)

        self._semantic_enabled = QCheckBox("Enable semantic (FAISS) search")
        self._semantic_enabled.setChecked(True)
        self._semantic_enabled.setStyleSheet(
            f"QCheckBox {{ color: #666; font-size: 13px; background: transparent; border: none; }}"
            f"QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid #333; border-radius: 4px; background: #0D0D0D; }}"
            f"QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}"
        )
        lay.addWidget(self._semantic_enabled)

        # ══════════════════════════════════════════
        # SECTION 5 — DATABASE
        # ══════════════════════════════════════════
        lay.addWidget(_section("DATABASE"))
        lay.addWidget(_separator())

        self._db_path_lbl = QLabel("Database: data/zenai.db")
        self._db_path_lbl.setStyleSheet("color: #333; font-size: 12px; background: transparent; border: none;")
        lay.addWidget(self._db_path_lbl)

        db_row = QHBoxLayout()
        rebuild_btn = QPushButton("🔄  Rebuild FAISS Index")
        rebuild_btn.setFixedHeight(34)
        rebuild_btn.setStyleSheet(self._ghost_btn("#f39c12"))
        rebuild_btn.clicked.connect(self._rebuild_index)
        self._rebuild_status = QLabel("")
        self._rebuild_status.setStyleSheet("color: #444; font-size: 11px; background: transparent; border: none;")
        db_row.addWidget(rebuild_btn)
        db_row.addWidget(self._rebuild_status)
        db_row.addStretch()
        lay.addLayout(db_row)

        # ══════════════════════════════════════════
        # SAVE BUTTON
        # ══════════════════════════════════════════
        lay.addSpacing(20)
        save_row = QHBoxLayout()
        self._save_btn = QPushButton("✓  Save Settings")
        self._save_btn.setFixedHeight(40)
        self._save_btn.setFixedWidth(180)
        self._save_btn.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: #000; border: none; border-radius: 8px; font-size: 14px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: #00C9D4; }}"
        )
        self._save_btn.clicked.connect(self._save)
        self._save_status = QLabel("")
        self._save_status.setStyleSheet(f"color: {ACCENT}; font-size: 12px; background: transparent; border: none;")
        save_row.addWidget(self._save_btn)
        save_row.addWidget(self._save_status)
        save_row.addStretch()
        lay.addLayout(save_row)

        # ══════════════════════════════════════════
        # SECTION 6 — ABOUT
        # ══════════════════════════════════════════
        lay.addSpacing(20)
        lay.addWidget(_section("ABOUT"))
        lay.addWidget(_separator())

        about_data = [
            ("App Name",    "Zen AI — Zendrix Multiverse OS"),
            ("Version",     "v1.3"),
            ("Author",      "Abdullah"),
            ("Database",    "SQLite + SQLAlchemy (21 tables)"),
            ("AI Backend",  "Multi-provider (Ollama / OpenAI / Gemini / Claude)"),
            ("Embeddings",  "Sentence Transformers  all-MiniLM-L6-v2 (384-dim)"),
            ("Vector DB",   "FAISS"),
            ("UI",          "PySide6 (Qt6)"),
            ("Graphs",      "NetworkX + PyVis (vis-network)"),
        ]
        for key, val in about_data:
            row = QHBoxLayout()
            k = QLabel(key)
            k.setFixedWidth(130)
            k.setStyleSheet("color: #333; font-size: 12px; background: transparent; border: none;")
            v = QLabel(val)
            v.setStyleSheet("color: #555; font-size: 12px; background: transparent; border: none;")
            row.addWidget(k)
            row.addWidget(v)
            row.addStretch()
            lay.addLayout(row)

        lay.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)

    # ── Provider switch ───────────────────────────────────

    def _on_provider_changed(self, idx: int):
        # Guard: may be called before all widgets are created
        if not hasattr(self, "_api_key_frame") or not hasattr(self, "_model_combo"):
            return
        p = PROVIDERS[idx]
        # Show/hide frames
        self._api_key_frame.setVisible(p["needs_key"])
        self._ollama_frame.setVisible(p["needs_url"])

        if p["api_label"]:
            self._api_key_label.setText(p["api_label"])

        self._model_combo.clear()
        self._model_combo.setEditable(False)   # reset first
        self._model_combo.addItems(p["models"])

        if p["id"] == "custom":
            self._model_combo.setEditable(True)
            self._model_combo.setPlaceholderText("Model name likhein...")


    def _toggle_key_vis(self, checked: bool):
        self._api_key_input.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password
        )
        self._show_key_btn.setText("🔒  Hide" if checked else "👁  Show")

    # ── Resolution ────────────────────────────────────────

    def _on_res_changed(self, idx: int):
        w, h = self._res_combo.itemData(idx)
        is_custom = (w is None)
        self._custom_res_frame.setVisible(is_custom)
        self._update_res_note()

    def _update_res_note(self):
        try:
            screen = QApplication.primaryScreen()
            g = screen.availableGeometry()
            self._res_note.setText(
                f"Current screen available: {g.width()} × {g.height()}  |  "
                f"Window resize is instant — no restart needed."
            )
        except Exception:
            pass

    def _apply_resolution(self):
        idx = self._res_combo.currentIndex()
        w, h = self._res_combo.itemData(idx)
        if w is None:
            # Custom
            try:
                w = int(self._custom_w.text())
                h = int(self._custom_h.text())
            except ValueError:
                self._res_note.setText("⚠  Custom resolution: width aur height integers hone chahiye.")
                self._res_note.setStyleSheet("color: #e74c3c; font-size: 10px; background: transparent; border: none;")
                return

        # Find main window and resize
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if widget.isVisible() and hasattr(widget, "resize"):
                widget.resize(w, h)
                # Center on screen
                screen = widget.screen()
                if screen:
                    center = screen.availableGeometry().center()
                    geo = widget.frameGeometry()
                    geo.moveCenter(center)
                    widget.move(geo.topLeft())
                break

        self._res_note.setText(f"✅  Window resized to {w} × {h}")
        self._res_note.setStyleSheet(f"color: #2ecc71; font-size: 10px; background: transparent; border: none;")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._res_note.setStyleSheet("color: #2A2A2A; font-size: 10px; background: transparent; border: none;"))

    # ── Test connection ───────────────────────────────────

    def _test_connection(self):
        pid = self._provider_combo.currentData()
        self._test_result.setText("Testing...")
        self._test_result.setStyleSheet("color: #888; font-size: 11px; background: transparent; border: none;")

        try:
            if pid == "ollama":
                import requests
                url = self._ollama_url.text().strip().rstrip("/")
                r = requests.get(f"{url}/api/tags", timeout=4)
                if r.status_code == 200:
                    models = [m["name"] for m in r.json().get("models", [])]
                    self._test_result.setText(f"✅  Connected  ({len(models)} models)")
                    self._test_result.setStyleSheet("color: #2ecc71; font-size: 11px; background: transparent; border: none;")
                else:
                    self._test_result.setText(f"⚠  HTTP {r.status_code}")
                    self._test_result.setStyleSheet("color: #f39c12; font-size: 11px; background: transparent; border: none;")

            elif pid == "openai":
                import requests
                key = self._api_key_input.text().strip()
                if not key:
                    self._test_result.setText("⚠  API key enter karein pehle")
                    return
                r = requests.get("https://api.openai.com/v1/models",
                                 headers={"Authorization": f"Bearer {key}"}, timeout=6)
                if r.status_code == 200:
                    count = len(r.json().get("data", []))
                    self._test_result.setText(f"✅  OpenAI key valid  ({count} models)")
                    self._test_result.setStyleSheet("color: #2ecc71; font-size: 11px; background: transparent; border: none;")
                else:
                    self._test_result.setText(f"❌  HTTP {r.status_code}: {r.json().get('error',{}).get('message','?')[:60]}")
                    self._test_result.setStyleSheet("color: #e74c3c; font-size: 11px; background: transparent; border: none;")

            elif pid == "gemini":
                import requests
                key = self._api_key_input.text().strip()
                if not key:
                    self._test_result.setText("⚠  Gemini API key enter karein")
                    return
                r = requests.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
                    timeout=6
                )
                if r.status_code == 200:
                    count = len(r.json().get("models", []))
                    self._test_result.setText(f"✅  Gemini key valid  ({count} models)")
                    self._test_result.setStyleSheet("color: #2ecc71; font-size: 11px; background: transparent; border: none;")
                else:
                    err = r.json().get("error", {}).get("message", "?")[:60]
                    self._test_result.setText(f"❌  {err}")
                    self._test_result.setStyleSheet("color: #e74c3c; font-size: 11px; background: transparent; border: none;")

            elif pid == "anthropic":
                import requests
                key = self._api_key_input.text().strip()
                if not key:
                    self._test_result.setText("⚠  Anthropic API key enter karein")
                    return
                r = requests.get("https://api.anthropic.com/v1/models",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                                 timeout=6)
                if r.status_code == 200:
                    self._test_result.setText("✅  Anthropic key valid")
                    self._test_result.setStyleSheet("color: #2ecc71; font-size: 11px; background: transparent; border: none;")
                else:
                    self._test_result.setText(f"❌  HTTP {r.status_code}")
                    self._test_result.setStyleSheet("color: #e74c3c; font-size: 11px; background: transparent; border: none;")

            elif pid == "custom":
                import requests
                url = self._ollama_url.text().strip().rstrip("/")
                key = self._api_key_input.text().strip()
                headers = {}
                if key:
                    headers["Authorization"] = f"Bearer {key}"
                r = requests.get(f"{url}/models", headers=headers, timeout=5)
                if r.status_code == 200:
                    self._test_result.setText("✅  Custom API reachable")
                    self._test_result.setStyleSheet("color: #2ecc71; font-size: 11px; background: transparent; border: none;")
                else:
                    self._test_result.setText(f"⚠  HTTP {r.status_code}")
                    self._test_result.setStyleSheet("color: #f39c12; font-size: 11px; background: transparent; border: none;")

        except Exception as e:
            self._test_result.setText(f"❌  {str(e)[:60]}")
            self._test_result.setStyleSheet("color: #e74c3c; font-size: 11px; background: transparent; border: none;")

    # ── Data load ─────────────────────────────────────────

    def _load_data(self):
        self._restore_ui_from_settings()
        self._worker = LoadSettingsDataWorker()
        self._worker.done.connect(self._on_data)
        self._worker.start()

    def _restore_ui_from_settings(self):
        """Populate all UI widgets from the persisted settings (called after UI is fully built)."""
        s = get_app_settings()

        # ── Provider ──
        saved_pid = s.ai_provider
        self._provider_combo.blockSignals(True)
        for i in range(self._provider_combo.count()):
            if self._provider_combo.itemData(i) == saved_pid:
                self._provider_combo.setCurrentIndex(i)
                break
        self._provider_combo.blockSignals(False)
        # Manually trigger UI update now
        self._on_provider_changed(self._provider_combo.currentIndex())

        # ── Model ──
        saved_model = s.ai_model
        idx = self._model_combo.findText(saved_model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        elif self._model_combo.isEditable():
            self._model_combo.setEditText(saved_model)

        # ── URL + Key + Temp ──
        self._ollama_url.setText(s.ollama_url)
        self._api_key_input.setText(s.api_key)
        self._temp_input.setText(str(s.temperature))

        # ── Display resolution ──
        dw, dh = s.display_size
        for ri in range(self._res_combo.count() - 1):   # skip last (Custom)
            val = self._res_combo.itemData(ri)
            if val and val[0] == dw and val[1] == dh:
                self._res_combo.setCurrentIndex(ri)
                break

        # ── Worldbuilding ──
        saved_canon = s.get("worldbuilding", "default_canon", "canon")
        for ci in range(self._default_canon.count()):
            if self._default_canon.itemData(ci) == saved_canon:
                self._default_canon.setCurrentIndex(ci)
                break
        score = s.get("worldbuilding", "default_score", 50)
        self._default_score.setText(str(score))

        # ── Search ──
        self._max_results.setText(str(s.get("search", "max_results", 25)))
        self._semantic_enabled.setChecked(bool(s.get("search", "semantic_enabled", True)))

    def _on_data(self, universes: list):
        self._universes = universes
        self._default_uni_combo.clear()
        self._default_uni_combo.addItem("— None —", None)
        for u in universes:
            self._default_uni_combo.addItem(u["name"], u["id"])

    # ── Rebuild index ─────────────────────────────────────

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

    # ── Save ──────────────────────────────────────────────

    def _save(self):
        s = get_app_settings()

        # AI section
        s.update_section("ai", {
            "provider":    self._provider_combo.currentData(),
            "model":       self._model_combo.currentText().strip(),
            "ollama_url":  self._ollama_url.text().strip(),
            "api_key":     self._api_key_input.text().strip(),
            "temperature": float(self._temp_input.text().strip() or "1.0"),
        })

        # Display section
        idx = self._res_combo.currentIndex()
        rw, rh = self._res_combo.itemData(idx)
        if rw is None:
            try:
                rw = int(self._custom_w.text())
                rh = int(self._custom_h.text())
            except ValueError:
                rw, rh = 1280, 800
        s.update_section("display", {"width": rw, "height": rh})

        # Worldbuilding section
        s.update_section("worldbuilding", {
            "default_universe_id": self._default_uni_combo.currentData(),
            "default_canon":       self._default_canon.currentData(),
            "default_score":       int(self._default_score.text().strip() or "50"),
        })

        # Search section
        s.update_section("search", {
            "max_results":      int(self._max_results.text().strip() or "25"),
            "semantic_enabled": self._semantic_enabled.isChecked(),
        })

        # Persist to disk
        s.save()

        # Rebuild AI client with new provider/model/key
        rebuild_client()

        # Apply resolution
        if rw and rh:
            self._apply_resolution()

        self._save_status.setText("✅  Settings saved  (config/user_settings.json)")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._save_status.setText(""))

    # ── Helper ────────────────────────────────────────────

    @staticmethod
    def _ghost_btn(color: str) -> str:
        return (
            f"QPushButton {{ background: transparent; color: {color}; "
            f"border: 1px solid {color}44; border-radius: 7px; "
            f"font-size: 12px; font-weight: 600; padding: 0 14px; }}"
            f"QPushButton:hover {{ background: {color}14; border-color: {color}; }}"
        )
