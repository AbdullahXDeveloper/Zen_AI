"""
app/ui/stories_view.py
Zen AI — Stories CRUD Page (Phase 9H)
Theme: Purple/Book  #8e44ad
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QLineEdit, QComboBox,
    QTextEdit, QMessageBox, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal

from app.database.db_init import get_session
from app.database import crud

ACCENT = "#8e44ad"
STORY_MODE_COLORS = {
    "canon":       "#00ADB5",
    "non_canon":   "#888",
    "what_if":     "#f39c12",
    "alt_timeline":"#9b59b6",
    "rpg_sim":     "#2ecc71",
}
STORY_MODES  = ["canon", "non_canon", "what_if", "alt_timeline", "rpg_sim"]
CANON_OPTIONS = ["canon", "non_canon", "alt_timeline", "experimental"]

MODE_ICONS = {
    "canon": "📖", "non_canon": "📝", "what_if": "🔮",
    "alt_timeline": "🌀", "rpg_sim": "🎲",
}


# ─── Workers ────────────────────────────────────────────
class LoadStoriesWorker(QThread):
    done  = Signal(list)
    error = Signal(str)

    def __init__(self, universe_id=None, story_mode=None, title_filter=None):
        super().__init__()
        self.universe_id  = universe_id
        self.story_mode   = story_mode
        self.title_filter = title_filter

    def run(self):
        try:
            session = get_session()
            stories = crud.list_stories(
                session,
                universe_id=self.universe_id,
                story_mode=self.story_mode or None,
                title_contains=self.title_filter or None,
            )
            result = [
                {
                    "id":           s.id,
                    "title":        s.title,
                    "summary":      s.summary or "",
                    "raw_text":     s.raw_text or "",
                    "story_mode":   s.story_mode,
                    "canon_status": s.canon_status,
                    "universe_id":  s.universe_id,
                    "universe_name": s.universe.name if s.universe else "—",
                }
                for s in stories
            ]
            session.close()
            self.done.emit(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class LoadUniversesForStoWorker(QThread):
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
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class SaveStoryWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, data: dict, story_id: int = None):
        super().__init__()
        self.data     = data
        self.story_id = story_id

    def run(self):
        try:
            session = get_session()
            if self.story_id:
                crud.update_story(session, self.story_id, **self.data)
            else:
                crud.create_story(session, **self.data)
            session.close()
            self.done.emit("ok")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class DeleteStoryWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, story_id: int):
        super().__init__()
        self.story_id = story_id

    def run(self):
        try:
            session = get_session()
            crud.delete_story(session, self.story_id)
            session.close()
            self.done.emit("ok")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


# ─── Story Card ─────────────────────────────────────────
class StoryCard(QFrame):
    edit_clicked   = Signal(dict)
    delete_clicked = Signal(dict)

    def __init__(self, data: dict):
        super().__init__()
        self.data  = data
        mode  = data.get("story_mode", "canon")
        color = STORY_MODE_COLORS.get(mode, ACCENT)
        icon  = MODE_ICONS.get(mode, "📖")

        self.setFixedHeight(165)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(f"""
            QFrame {{
                background: #111111; border: 1px solid #1E1E1E;
                border-top: 3px solid {color}; border-radius: 10px;
            }}
            QFrame:hover {{ background: #161616; border-color: #2A2A2A; border-top: 3px solid {color}; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(5)

        hdr = QHBoxLayout()
        title_lbl = QLabel(f"{icon}  {data['title']}")
        title_lbl.setStyleSheet("color: #EEEEEE; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        mode_lbl = QLabel(mode.replace("_", " ").upper())
        mode_lbl.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: 700; background: {color}18; border: 1px solid {color}44; border-radius: 4px; padding: 2px 8px;")
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        hdr.addWidget(mode_lbl)
        lay.addLayout(hdr)

        uni_lbl = QLabel(f"🌐 {data['universe_name']}")
        uni_lbl.setStyleSheet(f"color: {color}44; font-size: 10px; background: transparent; border: none;")
        lay.addWidget(uni_lbl)

        # Summary
        summary = data.get("summary", "")
        if summary:
            snippet = (summary[:100] + "…") if len(summary) > 100 else summary
            s_lbl = QLabel(snippet)
            s_lbl.setWordWrap(True)
            s_lbl.setStyleSheet("color: #404040; font-size: 11px; background: transparent; border: none;")
            lay.addWidget(s_lbl)

        # Word count of raw text
        raw = data.get("raw_text", "")
        if raw:
            wc = len(raw.split())
            wc_lbl = QLabel(f"📄 ~{wc:,} words")
            wc_lbl.setStyleSheet(f"color: {color}55; font-size: 10px; background: transparent; border: none;")
            lay.addWidget(wc_lbl)

        lay.addStretch()

        foot = QHBoxLayout()
        canon_lbl = QLabel(data["canon_status"].replace("_", " ").upper())
        canon_lbl.setStyleSheet(f"color: #333; font-size: 9px; background: transparent; border: none;")
        edit_btn = QPushButton("✎  Edit")
        edit_btn.setFixedSize(70, 26)
        edit_btn.setStyleSheet(self._btn(ACCENT))
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.data))
        del_btn = QPushButton("✕  Delete")
        del_btn.setFixedSize(80, 26)
        del_btn.setStyleSheet(self._btn("#e74c3c"))
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.data))
        foot.addWidget(canon_lbl)
        foot.addStretch()
        foot.addWidget(edit_btn)
        foot.addSpacing(6)
        foot.addWidget(del_btn)
        lay.addLayout(foot)

    @staticmethod
    def _btn(color):
        return f"QPushButton {{ background: transparent; color: {color}; border: 1px solid {color}44; border-radius: 5px; font-size: 11px; font-weight: 600; }} QPushButton:hover {{ background: {color}18; border-color: {color}; }}"


# ─── Form Panel ─────────────────────────────────────────
class StoryFormPanel(QFrame):
    saved     = Signal()
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._edit_id   = None
        self._worker    = None
        self._universes = []

        self.setFixedWidth(420)
        self.setStyleSheet("QFrame { background: #111111; border-left: 1px solid #1E1E1E; }")

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("background: #111111; border-bottom: 1px solid #1E1E1E;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 12, 0)
        h_lay.setSpacing(8)

        self._title = QLabel("New Story")
        self._title.setStyleSheet(f"color: {ACCENT}; font-size: 15px; font-weight: 800; background: transparent; border: none;")
        self._status = QLabel("")
        self._status.setStyleSheet("color: #e74c3c; font-size: 10px; background: transparent; border: none;")

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedSize(64, 30)
        self._cancel_btn.setStyleSheet("QPushButton { background: transparent; color: #666; border: 1px solid #333; border-radius: 5px; font-size: 12px; font-weight: 600; } QPushButton:hover { color: #AAA; border-color: #555; }")
        self._cancel_btn.clicked.connect(self._cancel)

        self._save_btn = QPushButton("✓  Save")
        self._save_btn.setFixedSize(80, 30)
        self._save_btn.setStyleSheet(f"QPushButton {{ background: {ACCENT}; color: #FFF; border: none; border-radius: 5px; font-size: 12px; font-weight: 700; }} QPushButton:hover {{ background: #9b59b6; }} QPushButton:disabled {{ background: #1A0A2A; color: #555; }}")
        self._save_btn.clicked.connect(self._save)

        x_btn = QPushButton("✕")
        x_btn.setFixedSize(28, 28)
        x_btn.setStyleSheet("QPushButton { background: transparent; color: #444; border: none; font-size: 14px; border-radius: 5px; } QPushButton:hover { color: #e74c3c; background: #1A1A1A; }")
        x_btn.clicked.connect(self._cancel)

        h_lay.addWidget(self._title)
        h_lay.addStretch()
        h_lay.addWidget(self._status)
        h_lay.addWidget(self._cancel_btn)
        h_lay.addWidget(self._save_btn)
        h_lay.addSpacing(4)
        h_lay.addWidget(x_btn)
        main.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #111111; } QScrollBar:vertical { background: #0D0D0D; width: 5px; } QScrollBar::handle:vertical { background: #2A2A2A; border-radius: 2px; }")
        fw = QWidget()
        fw.setStyleSheet("background: #111111;")
        lay = QVBoxLayout(fw)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(10)

        def _lbl(t):
            l = QLabel(t)
            l.setStyleSheet("color: #555; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent; border: none;")
            return l

        fs = f"QLineEdit, QTextEdit, QComboBox {{ background: #0D0D0D; color: #CCCCCC; border: 1px solid #222; border-radius: 6px; padding: 7px 12px; font-size: 13px; }} QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }} QComboBox QAbstractItemView {{ background: #111; color: #CCC; selection-background-color: {ACCENT}; }}"

        lay.addWidget(_lbl("UNIVERSE  (optional)"))
        self.universe_combo = QComboBox()
        self.universe_combo.setStyleSheet(fs)
        lay.addWidget(self.universe_combo)

        lay.addWidget(_lbl("TITLE  *"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g.  The Fall of Zendrix Prime")
        self.title_input.setStyleSheet(fs)
        lay.addWidget(self.title_input)

        lay.addWidget(_lbl("STORY MODE"))
        self.mode_combo = QComboBox()
        for m in STORY_MODES:
            icon = MODE_ICONS.get(m, "📖")
            self.mode_combo.addItem(f"{icon} {m.replace('_', ' ').title()}", m)
        self.mode_combo.setStyleSheet(fs)
        lay.addWidget(self.mode_combo)

        lay.addWidget(_lbl("CANON STATUS"))
        self.canon_combo = QComboBox()
        for opt in CANON_OPTIONS:
            self.canon_combo.addItem(opt.replace("_", " ").title(), opt)
        self.canon_combo.setStyleSheet(fs)
        lay.addWidget(self.canon_combo)

        lay.addWidget(_lbl("SUMMARY"))
        self.summary_input = QTextEdit()
        self.summary_input.setPlaceholderText("Short synopsis ya TL;DR...")
        self.summary_input.setFixedHeight(80)
        self.summary_input.setStyleSheet(fs)
        lay.addWidget(self.summary_input)

        lay.addWidget(_lbl("FULL TEXT  (optional — paste story here)"))
        self.raw_text_input = QTextEdit()
        self.raw_text_input.setPlaceholderText("Poori story yahan paste karein...")
        self.raw_text_input.setFixedHeight(130)
        self.raw_text_input.setStyleSheet(fs)
        lay.addWidget(self.raw_text_input)
        lay.addStretch()

        scroll.setWidget(fw)
        main.addWidget(scroll)

    def set_universes(self, universes: list):
        self._universes = universes
        self.universe_combo.clear()
        self.universe_combo.addItem("— No Universe —", None)
        for u in universes:
            self.universe_combo.addItem(u["name"], u["id"])

    def open_create(self):
        self._edit_id = None
        self._title.setText("New Story")
        self._status.setText("")
        self._save_btn.setEnabled(True)
        self.title_input.clear()
        self.summary_input.clear()
        self.raw_text_input.clear()
        self.mode_combo.setCurrentIndex(0)
        self.canon_combo.setCurrentIndex(0)
        self.universe_combo.setCurrentIndex(0)

    def open_edit(self, data: dict):
        self._edit_id = data["id"]
        self._title.setText("Edit Story")
        self._status.setText("")
        self._save_btn.setEnabled(True)
        self.universe_combo.setCurrentIndex(0)
        for i in range(self.universe_combo.count()):
            if self.universe_combo.itemData(i) == data["universe_id"]:
                self.universe_combo.setCurrentIndex(i)
                break
        self.title_input.setText(data["title"])
        self.summary_input.setPlainText(data["summary"])
        self.raw_text_input.setPlainText(data["raw_text"])
        for i in range(self.mode_combo.count()):
            if self.mode_combo.itemData(i) == data["story_mode"]:
                self.mode_combo.setCurrentIndex(i)
                break
        idx = CANON_OPTIONS.index(data["canon_status"]) if data["canon_status"] in CANON_OPTIONS else 0
        self.canon_combo.setCurrentIndex(idx)

    def _cancel(self):
        self.hide()
        self.cancelled.emit()

    def _save(self):
        title = self.title_input.text().strip()
        if not title:
            self._status.setText("⚠  Title required!")
            return

        payload = {
            "title":        title,
            "summary":      self.summary_input.toPlainText().strip() or None,
            "raw_text":     self.raw_text_input.toPlainText().strip() or None,
            "story_mode":   self.mode_combo.currentData(),
            "canon_status": self.canon_combo.currentData(),
            "universe_id":  self.universe_combo.currentData(),
        }
        self._save_btn.setEnabled(False)
        self._status.setText("Saving...")
        self._status.setStyleSheet(f"color: {ACCENT}; font-size: 10px; background: transparent; border: none;")
        self._worker = SaveStoryWorker(payload, self._edit_id)
        self._worker.done.connect(self._on_saved)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_saved(self, _):
        self.hide()
        self._save_btn.setEnabled(True)
        self._status.setText("")
        self.saved.emit()

    def _on_error(self, msg: str):
        self._status.setText(f"⚠  {msg}")
        self._status.setStyleSheet("color: #e74c3c; font-size: 10px; background: transparent; border: none;")
        self._save_btn.setEnabled(True)


# ─── Main View ──────────────────────────────────────────
class StoriesViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._load_worker   = None
        self._uni_worker    = None
        self._delete_worker = None
        self._stories       = []
        self._universes     = []
        self._setup_ui()
        self._load_universes()

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        main_area = QWidget()
        main_area.setStyleSheet("background: #0D0D0D;")
        left_lay = QVBoxLayout(main_area)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)

        top_bar = QFrame()
        top_bar.setFixedHeight(64)
        top_bar.setStyleSheet("background: #0D0D0D; border-bottom: 1px solid #1A1A1A;")
        bar_lay = QHBoxLayout(top_bar)
        bar_lay.setContentsMargins(32, 0, 32, 0)
        bar_lay.setSpacing(12)

        title = QLabel("📖  Stories")
        title.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: 900; letter-spacing: 2px; background: transparent; border: none;")
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #333; font-size: 11px; background: transparent; border: none;")
        self._new_btn = QPushButton("＋  New Story")
        self._new_btn.setFixedHeight(34)
        self._new_btn.setStyleSheet(f"QPushButton {{ background: {ACCENT}; color: #FFF; border: none; border-radius: 7px; padding: 0 18px; font-size: 13px; font-weight: 700; }} QPushButton:hover {{ background: #9b59b6; }}")
        self._new_btn.clicked.connect(self._open_create)

        bar_lay.addWidget(title)
        bar_lay.addStretch()
        bar_lay.addWidget(self._status_lbl)
        bar_lay.addWidget(self._new_btn)
        left_lay.addWidget(top_bar)

        filter_bar = QFrame()
        filter_bar.setFixedHeight(52)
        filter_bar.setStyleSheet("background: #0A0A0A; border-bottom: 1px solid #141414;")
        f_lay = QHBoxLayout(filter_bar)
        f_lay.setContentsMargins(32, 0, 32, 0)
        f_lay.setSpacing(12)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍  Search stories...")
        self._search_input.setFixedHeight(30)
        self._search_input.setFixedWidth(200)
        self._search_input.setStyleSheet(f"QLineEdit {{ background: #111; color: #CCC; border: 1px solid #222; border-radius: 6px; padding: 0 12px; font-size: 12px; }} QLineEdit:focus {{ border-color: {ACCENT}; }}")
        self._search_input.textChanged.connect(self._on_search_changed)

        combo_style = f"QComboBox {{ background: #111; color: #888; border: 1px solid #222; border-radius: 6px; padding: 0 10px; font-size: 12px; min-width: 130px; height: 30px; }} QComboBox QAbstractItemView {{ background: #111; color: #CCC; selection-background-color: {ACCENT}; }}"

        self._uni_combo = QComboBox()
        self._uni_combo.addItem("All Universes", None)
        self._uni_combo.setStyleSheet(combo_style)
        self._uni_combo.currentIndexChanged.connect(self._load_stories)

        self._mode_combo = QComboBox()
        self._mode_combo.addItem("All Modes", None)
        for m in STORY_MODES:
            icon = MODE_ICONS.get(m, "📖")
            self._mode_combo.addItem(f"{icon} {m.replace('_', ' ').title()}", m)
        self._mode_combo.setStyleSheet(combo_style)
        self._mode_combo.currentIndexChanged.connect(self._load_stories)

        f_lay.addWidget(self._search_input)
        f_lay.addWidget(self._uni_combo)
        f_lay.addWidget(self._mode_combo)
        f_lay.addStretch()
        left_lay.addWidget(filter_bar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(f"QScrollArea {{ border: none; background: #0D0D0D; }} QScrollBar:vertical {{ background: #111; width: 6px; }} QScrollBar::handle:vertical {{ background: #2A2A2A; border-radius: 3px; min-height: 20px; }} QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}")
        self._cards_widget = QWidget()
        self._cards_widget.setStyleSheet("background: #0D0D0D;")
        self._cards_layout = QGridLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(32, 24, 32, 32)
        self._cards_layout.setSpacing(16)
        self._cards_layout.setAlignment(Qt.AlignTop)
        self._scroll.setWidget(self._cards_widget)
        left_lay.addWidget(self._scroll)

        root.addWidget(main_area)

        self._form_panel = StoryFormPanel()
        self._form_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._form_panel.saved.connect(self._load_stories)
        self._form_panel.hide()
        root.addWidget(self._form_panel, 0)


    def _load_universes(self):
        self._uni_worker = LoadUniversesForStoWorker()
        self._uni_worker.done.connect(self._on_universes_loaded)
        self._uni_worker.error.connect(lambda _: self._load_stories())
        self._uni_worker.start()

    def _on_universes_loaded(self, universes: list):
        self._universes = universes
        self._uni_combo.blockSignals(True)
        self._uni_combo.clear()
        self._uni_combo.addItem("All Universes", None)
        for u in universes:
            self._uni_combo.addItem(u["name"], u["id"])
        self._uni_combo.blockSignals(False)
        self._form_panel.set_universes(universes)
        self._load_stories()

    def _open_create(self):
        self._form_panel.set_universes(self._universes)
        self._form_panel.open_create()
        self._form_panel.show()

    def _open_edit(self, data: dict):
        self._form_panel.set_universes(self._universes)
        self._form_panel.open_edit(data)
        self._form_panel.show()

    def _load_stories(self):
        self._status_lbl.setText("Loading...")
        self._new_btn.setEnabled(False)
        uid          = self._uni_combo.currentData()
        mode_filter  = self._mode_combo.currentData()
        title_filter = self._search_input.text().strip()
        self._load_worker = LoadStoriesWorker(uid, mode_filter, title_filter)
        self._load_worker.done.connect(self._on_loaded)
        self._load_worker.error.connect(self._on_error)
        self._load_worker.start()

    def _on_search_changed(self, text: str):
        if len(text) == 0 or len(text) >= 2:
            self._load_stories()

    def _on_loaded(self, stories: list):
        self._stories = stories
        self._rebuild_cards()
        count = len(stories)
        self._status_lbl.setText(f"{count} stor{'ies' if count != 1 else 'y'}")
        self._new_btn.setEnabled(True)

    def _on_error(self, msg: str):
        self._status_lbl.setText(f"Error: {msg}")
        self._new_btn.setEnabled(True)

    def _rebuild_cards(self):
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._stories:
            empty = QLabel("Koi story nahi mili.\n\nUpar '＋ New Story' click karein.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #222; font-size: 16px; padding: 60px; background: transparent; border: none;")
            self._cards_layout.addWidget(empty, 0, 0, 1, 3)
            return

        cols = 3
        for i, data in enumerate(self._stories):
            card = StoryCard(data)
            card.edit_clicked.connect(self._open_edit)
            card.delete_clicked.connect(self._confirm_delete)
            self._cards_layout.addWidget(card, i // cols, i % cols)

        remainder = len(self._stories) % cols
        if remainder:
            for j in range(cols - remainder):
                spacer = QWidget()
                spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._cards_layout.addWidget(spacer, len(self._stories) // cols, remainder + j)

    def _confirm_delete(self, data: dict):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete Story")
        dlg.setText(f"<b style='color:#e74c3c'>'{data['title']}'</b> delete karna chahte ho?<br><small style='color:#666'>Yeh action undo nahi hogi.</small>")
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        dlg.setDefaultButton(QMessageBox.Cancel)
        dlg.setStyleSheet("QMessageBox { background: #111; color: #CCC; font-size: 13px; } QPushButton { background: #1A1A1A; color: #CCC; border: 1px solid #333; border-radius: 6px; padding: 6px 20px; } QPushButton:hover { background: #222; }")
        if dlg.exec() == QMessageBox.Yes:
            self._delete_worker = DeleteStoryWorker(data["id"])
            self._delete_worker.done.connect(lambda _: self._load_stories())
            self._delete_worker.error.connect(self._on_error)
            self._delete_worker.start()
