"""
app/ui/story_writer_view.py
Zen AI — AI Story Writer (Module 11 Frontend)
Theme: Purple gradient  #8e44ad
Uses: app/ai/story_writer.py (generate_story + continue_story)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QLineEdit, QComboBox,
    QTextEdit, QSizePolicy, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal

from app.database.db_init import get_session
from app.database import crud

ACCENT = "#8e44ad"
STORY_MODES = ["canon", "non_canon", "what_if", "alt_timeline", "rpg_sim"]
MODE_ICONS  = {
    "canon": "📖", "non_canon": "📝", "what_if": "🔮",
    "alt_timeline": "🌀", "rpg_sim": "🎲",
}
MODE_COLORS = {
    "canon": "#00ADB5", "non_canon": "#888888",
    "what_if": "#f39c12", "alt_timeline": "#9b59b6", "rpg_sim": "#2ecc71",
}
LENGTH_OPTIONS = [("Short (~300 words)", "short"), ("Medium (~700 words)", "medium"), ("Long (~1500 words)", "long")]


# ─── Workers ────────────────────────────────────────────
class LoadStoryContextWorker(QThread):
    """Loads universes + characters for dropdowns."""
    done  = Signal(list, list)   # universes, characters
    error = Signal(str)

    def run(self):
        try:
            session = get_session()
            unis  = [{"id": u.id, "name": u.name} for u in crud.list_universes(session)]
            chars = [{"id": c.id, "name": c.name, "universe_id": c.universe_id}
                     for c in crud.list_characters(session)]
            session.close()
            self.done.emit(unis, chars)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class GenerateStoryWorker(QThread):
    done     = Signal(dict)
    progress = Signal(str)
    error    = Signal(str)

    def __init__(self, prompt, story_mode, universe_id, character_ids, target_length, title):
        super().__init__()
        self.prompt        = prompt
        self.story_mode    = story_mode
        self.universe_id   = universe_id
        self.character_ids = character_ids
        self.target_length = target_length
        self.title_input   = title

    def run(self):
        try:
            from app.ai.story_writer import generate_story
            self.progress.emit("Building lore context...")
            session = get_session()
            self.progress.emit(f"Generating {self.story_mode} story with Ollama...")
            result = generate_story(
                session,
                prompt        = self.prompt,
                story_mode    = self.story_mode,
                universe_id   = self.universe_id,
                character_ids = self.character_ids,
                target_length = self.target_length,
                title         = self.title_input or None,
            )
            session.close()
            self.done.emit(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class SaveGeneratedStoryWorker(QThread):
    done  = Signal(int)   # new story_id
    error = Signal(str)

    def __init__(self, title, summary, raw_text, story_mode, universe_id):
        super().__init__()
        self.title      = title
        self.summary    = summary
        self.raw_text   = raw_text
        self.story_mode = story_mode
        self.universe_id = universe_id

    def run(self):
        try:
            session = get_session()
            story = crud.create_story(
                session,
                title        = self.title,
                summary      = self.summary,
                raw_text     = self.raw_text,
                story_mode   = self.story_mode,
                canon_status = self.story_mode if self.story_mode in ("canon", "non_canon", "alt_timeline") else "experimental",
                universe_id  = self.universe_id,
            )
            sid = story.id
            session.close()
            self.done.emit(sid)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


# ─── Main Story Writer View ──────────────────────────────
class StoryWriterViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._ctx_worker  = None
        self._gen_worker  = None
        self._save_worker = None
        self._universes   = []
        self._characters  = []
        self._last_result = None
        self._setup_ui()
        self._load_context()

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

        title = QLabel("✦  AI Story Writer")
        title.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: 900; letter-spacing: 2px; background: transparent; border: none;")
        self._status_lbl = QLabel("Ollama-powered story generation grounded in your lore database")
        self._status_lbl.setStyleSheet("color: #2A2A2A; font-size: 11px; background: transparent; border: none;")
        bar_lay.addWidget(title)
        bar_lay.addStretch()
        bar_lay.addWidget(self._status_lbl)
        root.addWidget(top_bar)

        # ── Split: left = config, right = output ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1A1A1A; width: 1px; }")

        # ────── LEFT PANEL: Config ──────
        left = QFrame()
        left.setMinimumWidth(360)
        left.setMaximumWidth(440)
        left.setStyleSheet("background: #0A0A0A; border: none;")
        l_lay = QVBoxLayout(left)
        l_lay.setContentsMargins(0, 0, 0, 0)
        l_lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #0A0A0A; } QScrollBar:vertical { background: #111; width: 5px; } QScrollBar::handle:vertical { background: #2A2A2A; border-radius: 2px; }")
        fw = QWidget()
        fw.setStyleSheet("background: #0A0A0A;")
        f_lay = QVBoxLayout(fw)
        f_lay.setContentsMargins(24, 24, 24, 24)
        f_lay.setSpacing(12)

        def _lbl(t):
            l = QLabel(t)
            l.setStyleSheet("color: #444; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent; border: none;")
            return l

        fs = f"""
            QLineEdit, QTextEdit, QComboBox {{
                background: #111; color: #CCCCCC;
                border: 1px solid #1E1E1E; border-radius: 7px;
                padding: 8px 12px; font-size: 13px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
            QComboBox QAbstractItemView {{ background: #111; color: #CCC; selection-background-color: {ACCENT}; }}
        """

        # Story Mode
        f_lay.addWidget(_lbl("STORY MODE"))
        self.mode_combo = QComboBox()
        for m in STORY_MODES:
            self.mode_combo.addItem(f"{MODE_ICONS[m]}  {m.replace('_', ' ').title()}", m)
        self.mode_combo.setStyleSheet(fs)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        f_lay.addWidget(self.mode_combo)

        self._mode_hint = QLabel("")
        self._mode_hint.setWordWrap(True)
        self._mode_hint.setStyleSheet("color: #2A2A2A; font-size: 10px; font-style: italic; background: transparent; border: none;")
        f_lay.addWidget(self._mode_hint)

        # Universe
        f_lay.addWidget(_lbl("UNIVERSE  (optional)"))
        self.uni_combo = QComboBox()
        self.uni_combo.addItem("— No specific Universe —", None)
        self.uni_combo.setStyleSheet(fs)
        self.uni_combo.currentIndexChanged.connect(self._filter_characters)
        f_lay.addWidget(self.uni_combo)

        # Characters
        f_lay.addWidget(_lbl("FEATURE CHARACTERS  (optional, multi-select)"))
        self._char_hint = QLabel("Characters selected: 0")
        self._char_hint.setStyleSheet("color: #2A2A2A; font-size: 10px; background: transparent; border: none;")
        self.char_combo = QComboBox()
        self.char_combo.setStyleSheet(fs)
        self._selected_char_ids = []

        self._add_char_btn = QPushButton("＋ Add")
        self._add_char_btn.setFixedHeight(28)
        self._add_char_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {ACCENT}; border: 1px solid {ACCENT}44; border-radius: 5px; font-size: 11px; }} QPushButton:hover {{ background: {ACCENT}14; }}")
        self._add_char_btn.clicked.connect(self._add_character)

        self._char_pills = QLabel("")
        self._char_pills.setWordWrap(True)
        self._char_pills.setStyleSheet(f"color: {ACCENT}88; font-size: 10px; background: transparent; border: none;")

        char_row = QHBoxLayout()
        char_row.addWidget(self.char_combo)
        char_row.addWidget(self._add_char_btn)

        f_lay.addLayout(char_row)
        f_lay.addWidget(self._char_hint)
        f_lay.addWidget(self._char_pills)

        # Length
        f_lay.addWidget(_lbl("STORY LENGTH"))
        self.length_combo = QComboBox()
        for label, val in LENGTH_OPTIONS:
            self.length_combo.addItem(label, val)
        self.length_combo.setCurrentIndex(1)  # default medium
        self.length_combo.setStyleSheet(fs)
        f_lay.addWidget(self.length_combo)

        # Title (optional)
        f_lay.addWidget(_lbl("TITLE  (optional — leave blank for AI to decide)"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g.  The Last War of Zendrix Prime")
        self.title_input.setStyleSheet(fs)
        f_lay.addWidget(self.title_input)

        # Prompt
        f_lay.addWidget(_lbl("STORY PROMPT  *"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(
            "Describe what should happen in this story...\n\n"
            "e.g. OM_X confronts K for the first time after the Void War. "
            "The scene takes place in the Shattered Citadel. "
            "Tone: tense, philosophical."
        )
        self.prompt_input.setFixedHeight(130)
        self.prompt_input.setStyleSheet(fs)
        f_lay.addWidget(self.prompt_input)

        # Generate button
        self._gen_btn = QPushButton("✦  Generate Story")
        self._gen_btn.setFixedHeight(44)
        self._gen_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: #FFF;
                border: none; border-radius: 10px;
                font-size: 14px; font-weight: 800;
            }}
            QPushButton:hover {{ background: #9b59b6; }}
            QPushButton:disabled {{ background: #1A0A2A; color: #555; }}
        """)
        self._gen_btn.clicked.connect(self._generate)
        f_lay.addWidget(self._gen_btn)

        self._gen_status = QLabel("")
        self._gen_status.setAlignment(Qt.AlignCenter)
        self._gen_status.setStyleSheet(f"color: {ACCENT}; font-size: 11px; background: transparent; border: none;")
        f_lay.addWidget(self._gen_status)
        f_lay.addStretch()

        scroll.setWidget(fw)
        l_lay.addWidget(scroll)
        splitter.addWidget(left)

        # ────── RIGHT PANEL: Output ──────
        right = QFrame()
        right.setStyleSheet("background: #0D0D0D; border: none;")
        r_lay = QVBoxLayout(right)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(0)

        # Output header
        out_hdr = QFrame()
        out_hdr.setFixedHeight(52)
        out_hdr.setStyleSheet("background: #0D0D0D; border-bottom: 1px solid #141414;")
        oh_lay = QHBoxLayout(out_hdr)
        oh_lay.setContentsMargins(28, 0, 28, 0)
        oh_lay.setSpacing(12)

        self._output_title = QLabel("Generated Story")
        self._output_title.setStyleSheet(f"color: #333; font-size: 14px; font-weight: 700; background: transparent; border: none;")

        self._save_btn = QPushButton("💾  Save to Stories")
        self._save_btn.setFixedHeight(30)
        self._save_btn.setEnabled(False)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {ACCENT};
                border: 1px solid {ACCENT}44; border-radius: 7px;
                font-size: 12px; font-weight: 600; padding: 0 14px;
            }}
            QPushButton:hover {{ background: {ACCENT}14; border-color: {ACCENT}; }}
            QPushButton:disabled {{ color: #2A2A2A; border-color: #1A1A1A; }}
        """)
        self._save_btn.clicked.connect(self._save_story)

        self._copy_btn = QPushButton("📋  Copy")
        self._copy_btn.setFixedHeight(30)
        self._copy_btn.setEnabled(False)
        self._copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: #444;
                border: 1px solid #222; border-radius: 7px;
                font-size: 12px; font-weight: 600; padding: 0 14px;
            }}
            QPushButton:hover {{ color: #CCC; border-color: #444; }}
            QPushButton:disabled {{ color: #1A1A1A; border-color: #111; }}
        """)
        self._copy_btn.clicked.connect(self._copy_output)

        self._save_status = QLabel("")
        self._save_status.setStyleSheet("color: #2ecc71; font-size: 11px; background: transparent; border: none;")

        oh_lay.addWidget(self._output_title)
        oh_lay.addStretch()
        oh_lay.addWidget(self._save_status)
        oh_lay.addWidget(self._copy_btn)
        oh_lay.addWidget(self._save_btn)
        r_lay.addWidget(out_hdr)

        # RPG Choices panel (shown only for rpg_sim)
        self._choices_frame = QFrame()
        self._choices_frame.setStyleSheet("background: #0A0A0A; border-bottom: 1px solid #141414;")
        choices_lay = QHBoxLayout(self._choices_frame)
        choices_lay.setContentsMargins(28, 10, 28, 10)
        choices_lay.setSpacing(10)
        self._choices_lbl = QLabel("Player Choices:")
        self._choices_lbl.setStyleSheet(f"color: #2ecc71; font-size: 11px; font-weight: 700; background: transparent; border: none;")
        choices_lay.addWidget(self._choices_lbl)
        self._choice_btns_lay = QHBoxLayout()
        choices_lay.addLayout(self._choice_btns_lay)
        choices_lay.addStretch()
        self._choices_frame.hide()
        r_lay.addWidget(self._choices_frame)

        # Story output
        self._output_box = QTextEdit()
        self._output_box.setReadOnly(True)
        self._output_box.setPlaceholderText(
            "Story yahan appear hogi...\n\n"
            "Baayin taraf story settings configure karein aur '✦ Generate Story' click karein.\n\n"
            "Ollama (qwen2.5:7b) aapke lore database se characters, universes aur "
            "relationships ka context le kar story generate karega."
        )
        self._output_box.setStyleSheet(f"""
            QTextEdit {{
                background: #080808; color: #AAAAAA;
                border: none;
                padding: 28px 36px; font-size: 14px;
                line-height: 1.7;
                selection-background-color: {ACCENT}44;
            }}
            QScrollBar:vertical {{ background: #111; width: 6px; }}
            QScrollBar::handle:vertical {{ background: #2A2A2A; border-radius: 3px; min-height: 20px; }}
            QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
        """)
        r_lay.addWidget(self._output_box)

        splitter.addWidget(right)
        splitter.setSizes([400, 880])
        root.addWidget(splitter)

        # Init mode hint
        self._on_mode_changed(0)

    # ── Context Load ──────────────────────────────────────

    def _load_context(self):
        self._ctx_worker = LoadStoryContextWorker()
        self._ctx_worker.done.connect(self._on_context_loaded)
        self._ctx_worker.error.connect(lambda e: print(f"[Story Writer] Context load error: {e}"))
        self._ctx_worker.start()

    def _on_context_loaded(self, universes: list, characters: list):
        self._universes  = universes
        self._characters = characters

        self.uni_combo.blockSignals(True)
        self.uni_combo.clear()
        self.uni_combo.addItem("— No specific Universe —", None)
        for u in universes:
            self.uni_combo.addItem(u["name"], u["id"])
        self.uni_combo.blockSignals(False)

        self._populate_chars(characters)

    def _populate_chars(self, chars: list):
        self.char_combo.clear()
        self.char_combo.addItem("— Select character —", None)
        for c in chars:
            self.char_combo.addItem(c["name"], c["id"])

    def _filter_characters(self):
        uid = self.uni_combo.currentData()
        if uid is None:
            filtered = self._characters
        else:
            filtered = [c for c in self._characters if c["universe_id"] == uid]
        self._populate_chars(filtered)

    def _add_character(self):
        cid = self.char_combo.currentData()
        name = self.char_combo.currentText()
        if cid and cid not in self._selected_char_ids:
            self._selected_char_ids.append(cid)
            self._char_hint.setText(f"Characters selected: {len(self._selected_char_ids)}")
            pills = "  ".join(
                f"[{self.char_combo.itemText(i)}]"
                for i in range(self.char_combo.count())
                if self.char_combo.itemData(i) in self._selected_char_ids
            )
            self._char_pills.setText(pills or "")

    # ── Mode hint ─────────────────────────────────────────

    _HINTS = {
        "canon":       "Established lore ke saath consistent hona zaroori hai.",
        "non_canon":   "Side story — characters true rahenge, events optional.",
        "what_if":     "Alternate possibility — divergence point clear hoga.",
        "alt_timeline":"Alternate history — jo badla wo clearly noted hoga.",
        "rpg_sim":     "Decision point pe rukegi — 2-4 player choices milenge.",
    }

    def _on_mode_changed(self, _):
        mode = self.mode_combo.currentData() or "canon"
        self._mode_hint.setText(self._HINTS.get(mode, ""))

    # ── Generate ──────────────────────────────────────────

    def _generate(self):
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            self._gen_status.setText("⚠  Prompt required!")
            return

        self._gen_btn.setEnabled(False)
        self._save_btn.setEnabled(False)
        self._copy_btn.setEnabled(False)
        self._output_box.setPlainText("")
        self._output_title.setText("Generating...")
        self._output_title.setStyleSheet(f"color: {ACCENT}88; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        self._choices_frame.hide()
        self._last_result = None

        self._gen_worker = GenerateStoryWorker(
            prompt        = prompt,
            story_mode    = self.mode_combo.currentData(),
            universe_id   = self.uni_combo.currentData(),
            character_ids = self._selected_char_ids[:],
            target_length = self.length_combo.currentData(),
            title         = self.title_input.text().strip(),
        )
        self._gen_worker.progress.connect(self._on_progress)
        self._gen_worker.done.connect(self._on_generated)
        self._gen_worker.error.connect(self._on_gen_error)
        self._gen_worker.start()

    def _on_progress(self, msg: str):
        self._gen_status.setText(msg)

    def _on_generated(self, result: dict):
        self._gen_btn.setEnabled(True)
        self._gen_status.setText("")
        self._last_result = result

        title   = result.get("title", "Untitled")
        content = result.get("content", "")
        mode    = result.get("story_mode", "canon")
        choices = result.get("choices")

        color = MODE_COLORS.get(mode, ACCENT)
        self._output_title.setText(f"{MODE_ICONS.get(mode, '📖')}  {title}")
        self._output_title.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        self._output_box.setPlainText(content)

        self._save_btn.setEnabled(True)
        self._copy_btn.setEnabled(True)

        # RPG choices
        if choices:
            while self._choice_btns_lay.count():
                item = self._choice_btns_lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            for ch in choices:
                btn = QPushButton(ch[:60])
                btn.setFixedHeight(28)
                btn.setStyleSheet(f"QPushButton {{ background: #2ecc7114; color: #2ecc71; border: 1px solid #2ecc7144; border-radius: 5px; font-size: 11px; padding: 0 10px; }} QPushButton:hover {{ background: #2ecc7122; }}")
                self._choice_btns_lay.addWidget(btn)
            self._choices_frame.show()

    def _on_gen_error(self, msg: str):
        self._gen_btn.setEnabled(True)
        self._gen_status.setText(f"⚠  {msg}")
        self._output_box.setPlainText(f"[Error] {msg}\n\nOllama chal raha hai? Check karein: ollama serve")
        self._output_title.setText("Generation Failed")
        self._output_title.setStyleSheet("color: #e74c3c; font-size: 14px; font-weight: 700; background: transparent; border: none;")

    # ── Save ──────────────────────────────────────────────

    def _save_story(self):
        if not self._last_result:
            return
        r = self._last_result
        self._save_btn.setEnabled(False)
        self._save_status.setText("Saving...")

        self._save_worker = SaveGeneratedStoryWorker(
            title       = r.get("title", "Untitled"),
            summary     = r.get("content", "")[:300],
            raw_text    = r.get("content", ""),
            story_mode  = r.get("story_mode", "canon"),
            universe_id = r.get("universe_id"),
        )
        self._save_worker.done.connect(self._on_saved)
        self._save_worker.error.connect(lambda e: self._save_status.setText(f"⚠  {e}"))
        self._save_worker.start()

    def _on_saved(self, story_id: int):
        self._save_status.setText(f"✅  Saved (Story #{story_id})")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._save_status.setText(""))

    # ── Copy ──────────────────────────────────────────────

    def _copy_output(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._output_box.toPlainText())
        self._copy_btn.setText("✅  Copied!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self._copy_btn.setText("📋  Copy"))
