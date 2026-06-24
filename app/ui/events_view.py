"""
app/ui/events_view.py
Zen AI — Events CRUD Page (Phase 9G)
Theme: Red/Timeline  #e74c3c
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QLineEdit, QComboBox,
    QTextEdit, QSlider, QMessageBox, QGridLayout,
    QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal

from app.database.db_init import get_session
from app.database import crud
from app.ui.entity_links_widget import EntityLinksWidget

ACCENT = "#e74c3c"
CANON_COLORS = {
    "canon":        "#e74c3c",
    "non_canon":    "#888",
    "alt_timeline": "#9b59b6",
    "experimental": "#f39c12",
}
CANON_OPTIONS    = ["canon", "non_canon", "alt_timeline", "experimental"]
EVENT_TYPES      = ["birth", "death", "rebirth", "war", "other"]
EVENT_TYPE_ICONS = {
    "birth": "🌱", "death": "💀", "rebirth": "🔥",
    "war": "⚔", "other": "📌",
}


# ─── Workers ────────────────────────────────────────────
class LoadEventsWorker(QThread):
    done  = Signal(list)
    error = Signal(str)

    def __init__(self, universe_id=None, canon_filter=None, name_filter=None):
        super().__init__()
        self.universe_id  = universe_id
        self.canon_filter = canon_filter
        self.name_filter  = name_filter

    def run(self):
        try:
            session = get_session()
            evts = crud.list_events(
                session,
                universe_id=self.universe_id,
                canon_status=self.canon_filter or None,
                name_contains=self.name_filter or None,
            )
            result = [
                {
                    "id":               e.id,
                    "name":             e.name,
                    "description":      e.description or "",
                    "date_value":       e.date_value or "",
                    "date_label":       e.date_label or "",
                    "event_type":       e.event_type or "other",
                    "canon_status":     e.canon_status,
                    "importance_score": e.importance_score,
                    "universe_id":      e.universe_id,
                    "universe_name":    e.universe.name if e.universe else "—",
                }
                for e in evts
            ]
            session.close()
            self.done.emit(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class LoadParentsWorker(QThread):
    done  = Signal(dict)
    error = Signal(str)

    def run(self):
        try:
            session = get_session()
            from app.database import models
            unis = crud.list_universes(session)
            facs = session.query(models.Faction).all()
            roots = session.query(models.RootEntity).all()
            result = {
                "universes": [{"id": u.id, "name": u.name} for u in unis],
                "factions": [{"id": f.id, "name": f.name} for f in facs],
                "root_entities": [{"id": r.id, "name": r.name} for r in roots]
            }
            session.close()
            self.done.emit(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class SaveEventWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, data: dict, event_id: int = None):
        super().__init__()
        self.data     = data
        self.event_id = event_id

    def run(self):
        try:
            session = get_session()
            if self.event_id:
                crud.update_event(session, self.event_id, **self.data)
            else:
                crud.create_event(session, **self.data)
            session.close()
            self.done.emit("ok")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class DeleteEventWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, event_id: int):
        super().__init__()
        self.event_id = event_id

    def run(self):
        try:
            session = get_session()
            crud.delete_event(session, self.event_id)
            session.close()
            self.done.emit("ok")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


# ─── Event Card ─────────────────────────────────────────
class EventCard(QFrame):
    edit_clicked   = Signal(dict)
    delete_clicked = Signal(dict)

    def __init__(self, data: dict):
        super().__init__()
        self.data  = data
        color = CANON_COLORS.get(data["canon_status"], ACCENT)
        icon  = EVENT_TYPE_ICONS.get(data["event_type"], "📌")

        self.setFixedHeight(155)
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
        name_lbl = QLabel(f"{icon}  {data['name']}")
        name_lbl.setStyleSheet("color: #EEEEEE; font-size: 15px; font-weight: 700; background: transparent; border: none;")
        canon_lbl = QLabel(data["canon_status"].replace("_", " ").upper())
        canon_lbl.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: 700; background: {color}18; border: 1px solid {color}44; border-radius: 4px; padding: 2px 8px;")
        hdr.addWidget(name_lbl)
        hdr.addStretch()
        hdr.addWidget(canon_lbl)
        lay.addLayout(hdr)

        meta = QHBoxLayout()
        date_str = data["date_label"] or data["date_value"] or "No date"
        date_lbl = QLabel(f"📅 {date_str}")
        date_lbl.setStyleSheet(f"color: {color}66; font-size: 11px; background: transparent; border: none;")
        type_lbl = QLabel(f"🗂 {data['event_type'].title()}")
        type_lbl.setStyleSheet("color: #444; font-size: 11px; background: transparent; border: none;")
        uni_lbl = QLabel(f"🌐 {data['universe_name']}")
        uni_lbl.setStyleSheet("color: #333; font-size: 10px; background: transparent; border: none;")
        meta.addWidget(date_lbl)
        meta.addSpacing(10)
        meta.addWidget(type_lbl)
        meta.addSpacing(10)
        meta.addWidget(uni_lbl)
        meta.addStretch()
        lay.addLayout(meta)

        desc = data.get("description", "")
        if desc:
            snippet = (desc[:80] + "…") if len(desc) > 80 else desc
            d_lbl = QLabel(snippet)
            d_lbl.setWordWrap(True)
            d_lbl.setStyleSheet("color: #404040; font-size: 11px; background: transparent; border: none;")
            lay.addWidget(d_lbl)
        else:
            lay.addStretch()

        lay.addStretch()

        foot = QHBoxLayout()
        score_lbl = QLabel(f"★ {data['importance_score']}")
        score_lbl.setStyleSheet(f"color: {color}88; font-size: 11px; background: transparent; border: none;")
        edit_btn = QPushButton("✎  Edit")
        edit_btn.setFixedSize(70, 26)
        edit_btn.setStyleSheet(self._btn(ACCENT))
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.data))
        del_btn = QPushButton("✕  Delete")
        del_btn.setFixedSize(80, 26)
        del_btn.setStyleSheet(self._btn("#555555"))
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.data))
        foot.addWidget(score_lbl)
        foot.addStretch()
        foot.addWidget(edit_btn)
        foot.addSpacing(6)
        foot.addWidget(del_btn)
        lay.addLayout(foot)

    @staticmethod
    def _btn(color):
        return f"QPushButton {{ background: transparent; color: {color}; border: 1px solid {color}44; border-radius: 5px; font-size: 11px; font-weight: 600; }} QPushButton:hover {{ background: {color}18; border-color: {color}; }}"


# ─── Form Panel ─────────────────────────────────────────
class EventFormPanel(QFrame):
    saved     = Signal()
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._edit_id   = None
        self._worker        = None
        self._universes     = []
        self._factions      = []
        self._root_entities = []

        self.setFixedWidth(390)
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

        self._title = QLabel("New Event")
        self._title.setStyleSheet(f"color: {ACCENT}; font-size: 15px; font-weight: 800; background: transparent; border: none;")
        self._status = QLabel("")
        self._status.setStyleSheet("color: #e74c3c; font-size: 10px; background: transparent; border: none;")

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedSize(64, 30)
        self._cancel_btn.setStyleSheet("QPushButton { background: transparent; color: #666; border: 1px solid #333; border-radius: 5px; font-size: 12px; font-weight: 600; } QPushButton:hover { color: #AAA; border-color: #555; }")
        self._cancel_btn.clicked.connect(self._cancel)

        self._save_btn = QPushButton("✓  Save")
        self._save_btn.setFixedSize(80, 30)
        self._save_btn.setStyleSheet(f"QPushButton {{ background: {ACCENT}; color: #FFF; border: none; border-radius: 5px; font-size: 12px; font-weight: 700; }} QPushButton:hover {{ background: #c0392b; }} QPushButton:disabled {{ background: #2A0A0A; color: #555; }}")
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

        self.universe_label = _lbl("UNIVERSE")
        lay.addWidget(self.universe_label)
        self.universe_combo = QComboBox()
        self.universe_combo.setStyleSheet(fs)
        lay.addWidget(self.universe_combo)

        self.faction_label = _lbl("FACTION")
        lay.addWidget(self.faction_label)
        self.faction_combo = QComboBox()
        self.faction_combo.setStyleSheet(fs)
        lay.addWidget(self.faction_combo)

        self.root_entity_label = _lbl("ROOT ENTITY")
        lay.addWidget(self.root_entity_label)
        self.root_entity_combo = QComboBox()
        self.root_entity_combo.setStyleSheet(fs)
        lay.addWidget(self.root_entity_combo)

        self.universe_combo.currentIndexChanged.connect(self._on_universe_changed)
        self.faction_combo.currentIndexChanged.connect(self._on_faction_changed)
        self.root_entity_combo.currentIndexChanged.connect(self._on_root_entity_changed)

        lay.addWidget(_lbl("EVENT NAME  *"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g.  The Great Collapse")
        self.name_input.setStyleSheet(fs)
        lay.addWidget(self.name_input)

        lay.addWidget(_lbl("EVENT TYPE"))
        self.type_combo = QComboBox()
        for t in EVENT_TYPES:
            icon = EVENT_TYPE_ICONS.get(t, "📌")
            self.type_combo.addItem(f"{icon} {t.title()}", t)
        self.type_combo.setStyleSheet(fs)
        lay.addWidget(self.type_combo)

        # Custom type input — shown only when "other" is selected
        self.custom_type_input = QLineEdit()
        self.custom_type_input.setPlaceholderText("Custom event type name...")
        self.custom_type_input.setStyleSheet(fs)
        self.custom_type_input.hide()
        lay.addWidget(self.custom_type_input)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)

        lay.addWidget(_lbl("DATE VALUE  (sortable, e.g. 0001-03-15 or Era-5)"))
        self.date_value_input = QLineEdit()
        self.date_value_input.setPlaceholderText("e.g.  0521-07-01")
        self.date_value_input.setStyleSheet(fs)
        lay.addWidget(self.date_value_input)

        lay.addWidget(_lbl("DATE LABEL  (display text)"))
        self.date_label_input = QLineEdit()
        self.date_label_input.setPlaceholderText("e.g.  Year of the Void, Age 5")
        self.date_label_input.setStyleSheet(fs)
        lay.addWidget(self.date_label_input)

        lay.addWidget(_lbl("DESCRIPTION"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Event ka detail...")
        self.desc_input.setFixedHeight(80)
        self.desc_input.setStyleSheet(fs)
        lay.addWidget(self.desc_input)

        lay.addWidget(_lbl("CANON STATUS"))
        self.canon_combo = QComboBox()
        for opt in CANON_OPTIONS:
            self.canon_combo.addItem(opt.replace("_", " ").title(), opt)
        self.canon_combo.setStyleSheet(fs)
        lay.addWidget(self.canon_combo)

        lay.addWidget(_lbl("IMPORTANCE SCORE  (1 – 100)"))
        score_row = QHBoxLayout()
        self.score_slider = QSlider(Qt.Horizontal)
        self.score_slider.setRange(1, 100)
        self.score_slider.setValue(50)
        self.score_slider.setStyleSheet(f"QSlider::groove:horizontal {{ background: #1A1A1A; height: 6px; border-radius: 3px; }} QSlider::handle:horizontal {{ background: {ACCENT}; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }} QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}")
        self.score_val = QLabel("50")
        self.score_val.setFixedWidth(30)
        self.score_val.setStyleSheet(f"color: {ACCENT}; font-size: 13px; font-weight: 700; background: transparent; border: none;")
        self.score_slider.valueChanged.connect(lambda v: self.score_val.setText(str(v)))
        score_row.addWidget(self.score_slider)
        score_row.addWidget(self.score_val)
        lay.addLayout(score_row)
        # Story Links
        lay.addSpacing(8)
        self.story_links = EntityLinksWidget("event")
        lay.addWidget(self.story_links)

        lay.addStretch()

        scroll.setWidget(fw)
        main.addWidget(scroll)

    def set_parents(self, universes: list, factions: list, root_entities: list):
        self._universes = universes
        self._factions = factions
        self._root_entities = root_entities

        self.universe_combo.blockSignals(True)
        self.universe_combo.clear()
        self.universe_combo.addItem("None", None)
        for u in universes:
            self.universe_combo.addItem(u["name"], u["id"])
        self.universe_combo.blockSignals(False)

        self.faction_combo.blockSignals(True)
        self.faction_combo.clear()
        self.faction_combo.addItem("None", None)
        for f in factions:
            self.faction_combo.addItem(f["name"], f["id"])
        self.faction_combo.blockSignals(False)

        self.root_entity_combo.blockSignals(True)
        self.root_entity_combo.clear()
        self.root_entity_combo.addItem("None", None)
        for r in root_entities:
            self.root_entity_combo.addItem(r["name"], r["id"])
        self.root_entity_combo.blockSignals(False)

    def _update_visibility(self):
        u_val = self.universe_combo.currentData()
        f_val = self.faction_combo.currentData()
        r_val = self.root_entity_combo.currentData()

        if u_val is None and f_val is None and r_val is None:
            self.universe_label.setVisible(True)
            self.universe_combo.setVisible(True)
            self.faction_label.setVisible(True)
            self.faction_combo.setVisible(True)
            self.root_entity_label.setVisible(True)
            self.root_entity_combo.setVisible(True)
        else:
            self.universe_label.setVisible(u_val is not None)
            self.universe_combo.setVisible(u_val is not None)
            self.faction_label.setVisible(f_val is not None)
            self.faction_combo.setVisible(f_val is not None)
            self.root_entity_label.setVisible(r_val is not None)
            self.root_entity_combo.setVisible(r_val is not None)

    def _on_universe_changed(self, idx):
        if self.universe_combo.itemData(idx) is not None:
            self.faction_combo.blockSignals(True)
            self.root_entity_combo.blockSignals(True)
            self.faction_combo.setCurrentIndex(0)
            self.root_entity_combo.setCurrentIndex(0)
            self.faction_combo.blockSignals(False)
            self.root_entity_combo.blockSignals(False)
        self._update_visibility()

    def _on_faction_changed(self, idx):
        if self.faction_combo.itemData(idx) is not None:
            self.universe_combo.blockSignals(True)
            self.root_entity_combo.blockSignals(True)
            self.universe_combo.setCurrentIndex(0)
            self.root_entity_combo.setCurrentIndex(0)
            self.universe_combo.blockSignals(False)
            self.root_entity_combo.blockSignals(False)
        self._update_visibility()

    def _on_root_entity_changed(self, idx):
        if self.root_entity_combo.itemData(idx) is not None:
            self.universe_combo.blockSignals(True)
            self.faction_combo.blockSignals(True)
            self.universe_combo.setCurrentIndex(0)
            self.faction_combo.setCurrentIndex(0)
            self.universe_combo.blockSignals(False)
            self.faction_combo.blockSignals(False)
        self._update_visibility()

    def _on_type_changed(self, index: int):
        """Show/hide custom type input based on selection."""
        is_other = self.type_combo.currentData() == "other"
        self.custom_type_input.setVisible(is_other)
        if not is_other:
            self.custom_type_input.clear()

    def open_create(self):
        self._edit_id = None
        self._title.setText("New Event")
        self._status.setText("")
        self._save_btn.setEnabled(True)
        self.name_input.clear()
        self.desc_input.clear()
        self.date_value_input.clear()
        self.date_label_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.custom_type_input.clear()
        self.custom_type_input.hide()
        self.canon_combo.setCurrentIndex(0)
        self.score_slider.setValue(50)
        if self.universe_combo.count() > 0:
            self.universe_combo.setCurrentIndex(0)
        if self.faction_combo.count() > 0:
            self.faction_combo.setCurrentIndex(0)
        if self.root_entity_combo.count() > 0:
            self.root_entity_combo.setCurrentIndex(0)
        self._update_visibility()

    def open_edit(self, data: dict):
        self._edit_id = data["id"]
        self._title.setText("Edit Event")
        self._status.setText("")
        self._save_btn.setEnabled(True)
        for i in range(self.universe_combo.count()):
            if self.universe_combo.itemData(i) == data.get("universe_id"):
                self.universe_combo.setCurrentIndex(i)
                break
        for i in range(self.faction_combo.count()):
            if self.faction_combo.itemData(i) == data.get("faction_id"):
                self.faction_combo.setCurrentIndex(i)
                break
        for i in range(self.root_entity_combo.count()):
            if self.root_entity_combo.itemData(i) == data.get("root_entity_id"):
                self.root_entity_combo.setCurrentIndex(i)
                break
        self._update_visibility()
        self.name_input.setText(data["name"])
        self.desc_input.setPlainText(data["description"])
        self.date_value_input.setText(data["date_value"])
        self.date_label_input.setText(data["date_label"])
        et = data["event_type"]
        known_types = [self.type_combo.itemData(i) for i in range(self.type_combo.count())]
        if et in known_types:
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == et:
                    self.type_combo.setCurrentIndex(i)
                    break
            self.custom_type_input.clear()
            self.custom_type_input.hide()
        else:
            # Unknown custom type — select "other" and show custom input
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == "other":
                    self.type_combo.setCurrentIndex(i)
                    break
            self.custom_type_input.setText(et)
            self.custom_type_input.show()
        idx = CANON_OPTIONS.index(data["canon_status"]) if data["canon_status"] in CANON_OPTIONS else 0
        self.canon_combo.setCurrentIndex(idx)
        self.score_slider.setValue(data["importance_score"])
        self.story_links.load_for_entity(data["id"])

    def _cancel(self):
        self.hide()
        self.cancelled.emit()

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            self._status.setText("⚠  Name required!")
            return
        uid = self.universe_combo.currentData()
        fid = self.faction_combo.currentData()
        rid = self.root_entity_combo.currentData()

        if uid is None and fid is None and rid is None:
            self._status.setText("⚠  Koi parent select karein (Universe / Faction / Root)!")
            return

        payload = {
            "universe_id":      uid,
            "faction_id":       fid,
            "root_entity_id":   rid,
            "name":             name,
            "description":      self.desc_input.toPlainText().strip() or None,
            "date_value":       self.date_value_input.text().strip() or None,
            "date_label":       self.date_label_input.text().strip() or None,
            "event_type":       self.custom_type_input.text().strip() if self.type_combo.currentData() == "other" and self.custom_type_input.text().strip() else self.type_combo.currentData(),
            "canon_status":     self.canon_combo.currentData(),
            "importance_score": self.score_slider.value(),
        }
        self._save_btn.setEnabled(False)
        self._status.setText("Saving...")
        self._status.setStyleSheet(f"color: {ACCENT}; font-size: 10px; background: transparent; border: none;")
        self._worker = SaveEventWorker(payload, self._edit_id)
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
class EventsViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._load_worker   = None
        self._uni_worker    = None
        self._delete_worker = None
        self._events        = []
        self._universes     = []
        self._all_factions  = []
        self._root_entities = []
        self._setup_ui()
        self._load_parents()

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

        title = QLabel("📅  Events")
        title.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: 900; letter-spacing: 2px; background: transparent; border: none;")
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #333; font-size: 11px; background: transparent; border: none;")
        self._new_btn = QPushButton("＋  New Event")
        self._new_btn.setFixedHeight(34)
        self._new_btn.setStyleSheet(f"QPushButton {{ background: {ACCENT}; color: #FFF; border: none; border-radius: 7px; padding: 0 18px; font-size: 13px; font-weight: 700; }} QPushButton:hover {{ background: #c0392b; }}")
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
        self._search_input.setPlaceholderText("🔍  Search events...")
        self._search_input.setFixedHeight(30)
        self._search_input.setFixedWidth(200)
        self._search_input.setStyleSheet(f"QLineEdit {{ background: #111; color: #CCC; border: 1px solid #222; border-radius: 6px; padding: 0 12px; font-size: 12px; }} QLineEdit:focus {{ border-color: {ACCENT}; }}")
        self._search_input.textChanged.connect(self._on_search_changed)

        combo_style = f"QComboBox {{ background: #111; color: #888; border: 1px solid #222; border-radius: 6px; padding: 0 10px; font-size: 12px; min-width: 130px; height: 30px; }} QComboBox QAbstractItemView {{ background: #111; color: #CCC; selection-background-color: {ACCENT}; }}"

        self._uni_combo = QComboBox()
        self._uni_combo.addItem("All Universes", None)
        self._uni_combo.setStyleSheet(combo_style)
        self._uni_combo.currentIndexChanged.connect(self._load_events)

        self._canon_combo = QComboBox()
        self._canon_combo.addItem("All Canon Status", None)
        for opt in CANON_OPTIONS:
            self._canon_combo.addItem(opt.replace("_", " ").title(), opt)
        self._canon_combo.setStyleSheet(combo_style)
        self._canon_combo.currentIndexChanged.connect(self._load_events)

        f_lay.addWidget(self._search_input)
        f_lay.addWidget(self._uni_combo)
        f_lay.addWidget(self._canon_combo)
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

        self._form_panel = EventFormPanel()
        self._form_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._form_panel.saved.connect(self._load_events)
        self._form_panel.hide()
        root.addWidget(self._form_panel, 0)

    def showEvent(self, event):
        super().showEvent(event)
        # Refresh universe list every time tab is opened
        self._load_parents()

    def _load_parents(self):
        self._uni_worker = LoadParentsWorker()
        self._uni_worker.done.connect(self._on_parents_loaded)
        self._uni_worker.error.connect(lambda _: self._load_events())
        self._uni_worker.start()

    def _on_parents_loaded(self, data: dict):
        self._universes = data["universes"]
        self._all_factions = data["factions"]
        self._root_entities = data["root_entities"]

        self._uni_combo.blockSignals(True)
        self._uni_combo.clear()
        self._uni_combo.addItem("All Universes", None)
        for u in self._universes:
            self._uni_combo.addItem(u["name"], u["id"])
        self._uni_combo.blockSignals(False)
        self._form_panel.set_parents(self._universes, self._all_factions, self._root_entities)
        self._load_events()

    def _open_create(self):
        self._form_panel.set_parents(self._universes, self._all_factions, self._root_entities)
        self._form_panel.open_create()
        self._form_panel.show()

    def _open_edit(self, data: dict):
        self._form_panel.set_parents(self._universes, self._all_factions, self._root_entities)
        self._form_panel.open_edit(data)
        self._form_panel.show()

    def _load_events(self):
        self._status_lbl.setText("Loading...")
        self._new_btn.setEnabled(False)
        uid          = self._uni_combo.currentData()
        canon_filter = self._canon_combo.currentData()
        name_filter  = self._search_input.text().strip()
        self._load_worker = LoadEventsWorker(uid, canon_filter, name_filter)
        self._load_worker.done.connect(self._on_loaded)
        self._load_worker.error.connect(self._on_error)
        self._load_worker.start()

    def _on_search_changed(self, text: str):
        if len(text) == 0 or len(text) >= 2:
            self._load_events()

    def _on_loaded(self, events: list):
        self._events = events
        self._rebuild_cards()
        count = len(events)
        self._status_lbl.setText(f"{count} event{'s' if count != 1 else ''}")
        self._new_btn.setEnabled(True)

    def _on_error(self, msg: str):
        self._status_lbl.setText(f"Error: {msg}")
        self._new_btn.setEnabled(True)

    def _rebuild_cards(self):
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._events:
            empty = QLabel("Koi event nahi mila.\n\nUpar '＋ New Event' click karein.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #222; font-size: 16px; padding: 60px; background: transparent; border: none;")
            self._cards_layout.addWidget(empty, 0, 0, 1, 3)
            return

        cols = 3
        for i, data in enumerate(self._events):
            card = EventCard(data)
            card.edit_clicked.connect(self._open_edit)
            card.delete_clicked.connect(self._confirm_delete)
            self._cards_layout.addWidget(card, i // cols, i % cols)

        remainder = len(self._events) % cols
        if remainder:
            for j in range(cols - remainder):
                spacer = QWidget()
                spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._cards_layout.addWidget(spacer, len(self._events) // cols, remainder + j)

    def _confirm_delete(self, data: dict):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete Event")
        dlg.setText(f"<b style='color:#e74c3c'>'{data['name']}'</b> delete karna chahte ho?<br><small style='color:#666'>Yeh action undo nahi hogi.</small>")
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        dlg.setDefaultButton(QMessageBox.Cancel)
        dlg.setStyleSheet("QMessageBox { background: #111; color: #CCC; font-size: 13px; } QPushButton { background: #1A1A1A; color: #CCC; border: 1px solid #333; border-radius: 6px; padding: 6px 20px; } QPushButton:hover { background: #222; }")
        if dlg.exec() == QMessageBox.Yes:
            self._delete_worker = DeleteEventWorker(data["id"])
            self._delete_worker.done.connect(lambda _: self._load_events())
            self._delete_worker.error.connect(self._on_error)
            self._delete_worker.start()
