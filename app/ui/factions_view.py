"""
app/ui/factions_view.py
Zen AI — Factions CRUD Page (Phase 9D)

Pattern: same as universes_view.py (Log_11 standard)
  - Fixed 60px header: [Title] [status] [Cancel] [✓ Save] [✕]
  - Scrollable fields in middle
  - Panel closes itself via self.hide() on save/cancel
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


# ─────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────
CANON_COLORS = {
    "canon":        "#f39c12",   # orange/gold — distinct from Universes/Characters
    "non_canon":    "#e74c3c",
    "alt_timeline": "#9b59b6",
    "experimental": "#3498db",
}
CANON_OPTIONS = ["canon", "non_canon", "alt_timeline", "experimental"]
ACCENT = "#f39c12"   # gold theme for Factions


# ─────────────────────────────────────────────────────────
# Workers
# ─────────────────────────────────────────────────────────
class LoadFactionsWorker(QThread):
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
            facs = crud.list_factions(
                session,
                universe_id=self.universe_id,
                canon_status=self.canon_filter or None,
                name_contains=self.name_filter or None,
            )
            result = [
                {
                    "id":               f.id,
                    "name":             f.name,
                    "description":      f.description or "",
                    "ideology":         f.ideology or "",
                    "canon_status":     f.canon_status,
                    "importance_score": f.importance_score,
                    "universe_id":      f.universe_id,
                    "universe_name":    f.universe.name if f.universe else "—",
                    "founder_id":       f.founder_id,
                }
                for f in facs
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


class SaveFactionWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, data: dict, faction_id: int = None):
        super().__init__()
        self.data       = data
        self.faction_id = faction_id

    def run(self):
        try:
            session = get_session()
            if self.faction_id:
                crud.update_faction(session, self.faction_id, **self.data)
            else:
                crud.create_faction(session, **self.data)
            session.close()
            self.done.emit("ok")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class DeleteFactionWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, faction_id: int):
        super().__init__()
        self.faction_id = faction_id

    def run(self):
        try:
            session = get_session()
            crud.delete_faction(session, self.faction_id)
            session.close()
            self.done.emit("ok")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


# ─────────────────────────────────────────────────────────
# Faction Card
# ─────────────────────────────────────────────────────────
class FactionCard(QFrame):
    edit_clicked   = Signal(dict)
    delete_clicked = Signal(dict)

    def __init__(self, data: dict):
        super().__init__()
        self.data  = data
        color = CANON_COLORS.get(data["canon_status"], ACCENT)

        self.setFixedHeight(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(f"""
            QFrame {{
                background: #111111;
                border: 1px solid #1E1E1E;
                border-top: 3px solid {color};
                border-radius: 10px;
            }}
            QFrame:hover {{
                background: #161616;
                border-color: #2A2A2A;
                border-top: 3px solid {color};
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(6)

        # ── Header row ──
        hdr = QHBoxLayout()
        name_lbl = QLabel(f"⚔  {data['name']}")
        name_lbl.setStyleSheet(
            "color: #EEEEEE; font-size: 15px; font-weight: 700; "
            "background: transparent; border: none;"
        )
        canon_lbl = QLabel(data["canon_status"].replace("_", " ").upper())
        canon_lbl.setStyleSheet(
            f"color: {color}; font-size: 9px; font-weight: 700; "
            f"background: {color}18; border: 1px solid {color}44; "
            "border-radius: 4px; padding: 2px 8px;"
        )
        hdr.addWidget(name_lbl)
        hdr.addStretch()
        hdr.addWidget(canon_lbl)
        lay.addLayout(hdr)

        # ── Universe ──
        uni_lbl = QLabel(f"🌐 {data['universe_name']}")
        uni_lbl.setStyleSheet(
            "color: #444; font-size: 11px; background: transparent; border: none;"
        )
        lay.addWidget(uni_lbl)

        # ── Ideology snippet ──
        ideology = data.get("ideology", "")
        if ideology:
            snippet = (ideology[:70] + "…") if len(ideology) > 70 else ideology
            id_lbl = QLabel(f"💡 {snippet}")
            id_lbl.setWordWrap(True)
            id_lbl.setStyleSheet(
                f"color: {color}66; font-size: 11px; background: transparent; border: none;"
            )
            lay.addWidget(id_lbl)
        else:
            # Description fallback
            desc = data.get("description", "")
            if desc:
                snippet = (desc[:80] + "…") if len(desc) > 80 else desc
                d_lbl = QLabel(snippet)
                d_lbl.setWordWrap(True)
                d_lbl.setStyleSheet(
                    "color: #404040; font-size: 11px; background: transparent; border: none;"
                )
                lay.addWidget(d_lbl)

        lay.addStretch()

        # ── Footer ──
        foot = QHBoxLayout()
        score_lbl = QLabel(f"★ {data['importance_score']}")
        score_lbl.setStyleSheet(
            f"color: {color}88; font-size: 11px; background: transparent; border: none;"
        )
        edit_btn = QPushButton("✎  Edit")
        edit_btn.setFixedSize(70, 26)
        edit_btn.setStyleSheet(self._action_btn(ACCENT))
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.data))

        del_btn = QPushButton("✕  Delete")
        del_btn.setFixedSize(80, 26)
        del_btn.setStyleSheet(self._action_btn("#e74c3c"))
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.data))

        foot.addWidget(score_lbl)
        foot.addStretch()
        foot.addWidget(edit_btn)
        foot.addSpacing(6)
        foot.addWidget(del_btn)
        lay.addLayout(foot)

    @staticmethod
    def _action_btn(color: str) -> str:
        return f"""
            QPushButton {{
                background: transparent; color: {color};
                border: 1px solid {color}44; border-radius: 5px;
                font-size: 11px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {color}18; border-color: {color}; }}
        """


# ─────────────────────────────────────────────────────────
# Faction Form Panel  (Log_11 standard panel design)
# ─────────────────────────────────────────────────────────
class FactionFormPanel(QFrame):
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

        # ── Fixed Header (title + Cancel + Save + ✕) ──
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("background: #111111; border-bottom: 1px solid #1E1E1E;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 12, 0)
        h_lay.setSpacing(8)

        self._title = QLabel("New Faction")
        self._title.setStyleSheet(
            f"color: {ACCENT}; font-size: 15px; font-weight: 800; "
            "background: transparent; border: none;"
        )

        self._status = QLabel("")
        self._status.setStyleSheet(
            "color: #e74c3c; font-size: 10px; background: transparent; border: none;"
        )

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedHeight(30)
        self._cancel_btn.setFixedWidth(64)
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #666;
                border: 1px solid #333; border-radius: 5px;
                font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { color: #AAA; border-color: #555; }
        """)
        self._cancel_btn.clicked.connect(self._cancel)

        self._save_btn = QPushButton("✓  Save")
        self._save_btn.setFixedHeight(30)
        self._save_btn.setFixedWidth(80)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: #000;
                border: none; border-radius: 5px;
                font-size: 12px; font-weight: 700;
            }}
            QPushButton:hover {{ background: #f5ab35; }}
            QPushButton:disabled {{ background: #3A2A00; color: #555; }}
        """)
        self._save_btn.clicked.connect(self._save)

        x_btn = QPushButton("✕")
        x_btn.setFixedSize(28, 28)
        x_btn.setToolTip("Close")
        x_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #444;
                border: none; font-size: 14px; border-radius: 5px;
            }
            QPushButton:hover { color: #e74c3c; background: #1A1A1A; }
        """)
        x_btn.clicked.connect(self._cancel)

        h_lay.addWidget(self._title)
        h_lay.addStretch()
        h_lay.addWidget(self._status)
        h_lay.addWidget(self._cancel_btn)
        h_lay.addWidget(self._save_btn)
        h_lay.addSpacing(4)
        h_lay.addWidget(x_btn)
        main.addWidget(header)

        # ── Scrollable Fields ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: #111111; }
            QScrollBar:vertical { background: #0D0D0D; width: 5px; }
            QScrollBar::handle:vertical { background: #2A2A2A; border-radius: 2px; }
        """)
        fw = QWidget()
        fw.setStyleSheet("background: #111111;")
        lay = QVBoxLayout(fw)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(10)

        def _lbl(t):
            l = QLabel(t)
            l.setStyleSheet(
                "color: #555; font-size: 10px; font-weight: 700; "
                "letter-spacing: 1px; background: transparent; border: none;"
            )
            return l

        fs = f"""
            QLineEdit, QTextEdit, QComboBox {{
                background: #0D0D0D; color: #CCCCCC;
                border: 1px solid #222; border-radius: 6px;
                padding: 7px 12px; font-size: 13px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
            QComboBox QAbstractItemView {{
                background: #111; color: #CCC;
                selection-background-color: {ACCENT};
            }}
        """

        # Universe
        self.universe_label = _lbl("UNIVERSE")
        lay.addWidget(self.universe_label)
        self.universe_combo = QComboBox()
        self.universe_combo.setStyleSheet(fs)
        lay.addWidget(self.universe_combo)

        # Faction
        self.faction_label = _lbl("FACTION")
        lay.addWidget(self.faction_label)
        self.faction_combo = QComboBox()
        self.faction_combo.setStyleSheet(fs)
        lay.addWidget(self.faction_combo)

        # Root Entity
        self.root_entity_label = _lbl("ROOT ENTITY")
        lay.addWidget(self.root_entity_label)
        self.root_entity_combo = QComboBox()
        self.root_entity_combo.setStyleSheet(fs)
        lay.addWidget(self.root_entity_combo)

        # Exclusive selection logic
        self.universe_combo.currentIndexChanged.connect(self._on_universe_changed)
        self.faction_combo.currentIndexChanged.connect(self._on_faction_changed)
        self.root_entity_combo.currentIndexChanged.connect(self._on_root_entity_changed)

        # Name
        lay.addWidget(_lbl("FACTION NAME  *"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g.  The Shadow Council")
        self.name_input.setStyleSheet(fs)
        lay.addWidget(self.name_input)

        # Description
        lay.addWidget(_lbl("DESCRIPTION"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Faction ki overall description...")
        self.desc_input.setFixedHeight(80)
        self.desc_input.setStyleSheet(fs)
        lay.addWidget(self.desc_input)

        # Ideology
        lay.addWidget(_lbl("IDEOLOGY"))
        self.ideology_input = QTextEdit()
        self.ideology_input.setPlaceholderText("Faction ki beliefs, goals, worldview...")
        self.ideology_input.setFixedHeight(72)
        self.ideology_input.setStyleSheet(fs)
        lay.addWidget(self.ideology_input)

        # Canon Status
        lay.addWidget(_lbl("CANON STATUS"))
        self.canon_combo = QComboBox()
        for opt in CANON_OPTIONS:
            self.canon_combo.addItem(opt.replace("_", " ").title(), opt)
        self.canon_combo.setStyleSheet(fs)
        lay.addWidget(self.canon_combo)

        # Importance Score
        lay.addWidget(_lbl("IMPORTANCE SCORE  (1 – 100)"))
        score_row = QHBoxLayout()
        self.score_slider = QSlider(Qt.Horizontal)
        self.score_slider.setRange(1, 100)
        self.score_slider.setValue(50)
        self.score_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ background: #1A1A1A; height: 6px; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: {ACCENT}; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }}
            QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
        """)
        self.score_val = QLabel("50")
        self.score_val.setFixedWidth(30)
        self.score_val.setStyleSheet(
            f"color: {ACCENT}; font-size: 13px; font-weight: 700; background: transparent; border: none;"
        )
        self.score_slider.valueChanged.connect(lambda v: self.score_val.setText(str(v)))
        score_row.addWidget(self.score_slider)
        score_row.addWidget(self.score_val)
        lay.addLayout(score_row)
        # Story Links
        lay.addSpacing(8)
        self.story_links = EntityLinksWidget("faction")
        lay.addWidget(self.story_links)

        lay.addStretch()

        scroll.setWidget(fw)
        main.addWidget(scroll)

    # ── Parent dropdowns ──────────────────────────────────

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

    # ── Exclusive Logic ────────────────────────────────────────

    def _update_visibility(self):
        u_val = self.universe_combo.currentData()
        f_val = self.faction_combo.currentData()
        r_val = self.root_entity_combo.currentData()

        # If all are None, show all
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

    # ── Public API ─────────────────────────────────────────

    def open_create(self):
        self._edit_id = None
        self._title.setText("New Faction")
        self._status.setText("")
        self._save_btn.setEnabled(True)
        self.name_input.clear()
        self.desc_input.clear()
        self.ideology_input.clear()
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
        self._title.setText("Edit Faction")
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
        self.ideology_input.setPlainText(data["ideology"])
        idx = CANON_OPTIONS.index(data["canon_status"]) if data["canon_status"] in CANON_OPTIONS else 0
        self.canon_combo.setCurrentIndex(idx)
        self.score_slider.setValue(data["importance_score"])
        self.story_links.load_for_entity(data["id"])

    # ── Internal ───────────────────────────────────────────

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
            "ideology":         self.ideology_input.toPlainText().strip() or None,
            "canon_status":     self.canon_combo.currentData(),
            "importance_score": self.score_slider.value(),
        }

        self._save_btn.setEnabled(False)
        self._status.setText("Saving...")
        self._status.setStyleSheet(
            f"color: {ACCENT}; font-size: 10px; background: transparent; border: none;"
        )

        self._worker = SaveFactionWorker(payload, self._edit_id)
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
        self._status.setStyleSheet(
            "color: #e74c3c; font-size: 10px; background: transparent; border: none;"
        )
        self._save_btn.setEnabled(True)


# ─────────────────────────────────────────────────────────
# Main Factions View
# ─────────────────────────────────────────────────────────
class FactionsViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._load_worker   = None
        self._uni_worker    = None
        self._delete_worker = None
        self._factions      = []
        self._universes     = []
        self._all_factions  = []
        self._root_entities = []
        self._setup_ui()
        self._load_parents()

    # ── Build UI ──────────────────────────────────────────

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left: Main area ──
        main_area = QWidget()
        main_area.setStyleSheet("background: #0D0D0D;")
        left_lay = QVBoxLayout(main_area)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)

        # ── Top bar ──
        top_bar = QFrame()
        top_bar.setFixedHeight(64)
        top_bar.setStyleSheet("background: #0D0D0D; border-bottom: 1px solid #1A1A1A;")
        bar_lay = QHBoxLayout(top_bar)
        bar_lay.setContentsMargins(32, 0, 32, 0)
        bar_lay.setSpacing(12)

        title = QLabel("⚔  Factions")
        title.setStyleSheet(
            f"color: {ACCENT}; font-size: 20px; font-weight: 900; "
            "letter-spacing: 2px; background: transparent; border: none;"
        )
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(
            "color: #333; font-size: 11px; background: transparent; border: none;"
        )

        self._new_btn = QPushButton("＋  New Faction")
        self._new_btn.setFixedHeight(34)
        self._new_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: #000;
                border: none; border-radius: 7px;
                padding: 0 18px; font-size: 13px; font-weight: 700;
            }}
            QPushButton:hover {{ background: #f5ab35; }}
        """)
        self._new_btn.clicked.connect(self._open_create)

        bar_lay.addWidget(title)
        bar_lay.addStretch()
        bar_lay.addWidget(self._status_lbl)
        bar_lay.addWidget(self._new_btn)
        left_lay.addWidget(top_bar)

        # ── Filter bar ──
        filter_bar = QFrame()
        filter_bar.setFixedHeight(52)
        filter_bar.setStyleSheet("background: #0A0A0A; border-bottom: 1px solid #141414;")
        f_lay = QHBoxLayout(filter_bar)
        f_lay.setContentsMargins(32, 0, 32, 0)
        f_lay.setSpacing(12)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍  Search factions...")
        self._search_input.setFixedHeight(30)
        self._search_input.setFixedWidth(220)
        self._search_input.setStyleSheet(f"""
            QLineEdit {{
                background: #111; color: #CCC;
                border: 1px solid #222; border-radius: 6px;
                padding: 0 12px; font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {ACCENT}; }}
        """)
        self._search_input.textChanged.connect(self._on_search_changed)

        combo_style = f"""
            QComboBox {{
                background: #111; color: #888;
                border: 1px solid #222; border-radius: 6px;
                padding: 0 10px; font-size: 12px;
                min-width: 140px; height: 30px;
            }}
            QComboBox:hover {{ border-color: #333; }}
            QComboBox QAbstractItemView {{
                background: #111; color: #CCC;
                selection-background-color: {ACCENT};
            }}
        """

        self._uni_combo = QComboBox()
        self._uni_combo.addItem("All Universes", None)
        self._uni_combo.setStyleSheet(combo_style)
        self._uni_combo.currentIndexChanged.connect(self._load_factions)

        self._canon_combo = QComboBox()
        self._canon_combo.addItem("All Canon Status", None)
        for opt in CANON_OPTIONS:
            self._canon_combo.addItem(opt.replace("_", " ").title(), opt)
        self._canon_combo.setStyleSheet(combo_style)
        self._canon_combo.currentIndexChanged.connect(self._load_factions)

        f_lay.addWidget(self._search_input)
        f_lay.addWidget(self._uni_combo)
        f_lay.addWidget(self._canon_combo)
        f_lay.addStretch()
        left_lay.addWidget(filter_bar)

        # ── Cards scroll area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: #0D0D0D; }}
            QScrollBar:vertical {{ background: #111; width: 6px; border-radius: 3px; }}
            QScrollBar::handle:vertical {{ background: #2A2A2A; border-radius: 3px; min-height: 20px; }}
            QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
        """)

        self._cards_widget = QWidget()
        self._cards_widget.setStyleSheet("background: #0D0D0D;")
        self._cards_layout = QGridLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(32, 24, 32, 32)
        self._cards_layout.setSpacing(16)
        self._cards_layout.setAlignment(Qt.AlignTop)

        self._scroll.setWidget(self._cards_widget)
        left_lay.addWidget(self._scroll)

        root.addWidget(main_area)

        # ── Right: Slide-in form panel ──
        self._form_panel = FactionFormPanel()
        self._form_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._form_panel.saved.connect(self._load_factions)
        self._form_panel.hide()
        root.addWidget(self._form_panel, 0)

    def showEvent(self, event):
        super().showEvent(event)
        # Refresh universe list every time tab is opened
        self._load_parents()

    # ── Universe loading ───────────────────────────────────

    def _load_parents(self):
        self._uni_worker = LoadParentsWorker()
        self._uni_worker.done.connect(self._on_parents_loaded)
        self._uni_worker.error.connect(lambda _: self._load_factions())
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
        self._load_factions()

    # ── Panel open/close ──────────────────────────────────

    def _open_create(self):
        self._form_panel.set_parents(self._universes, self._all_factions, self._root_entities)
        self._form_panel.open_create()
        self._form_panel.show()

    def _open_edit(self, data: dict):
        self._form_panel.set_parents(self._universes, self._all_factions, self._root_entities)
        self._form_panel.open_edit(data)
        self._form_panel.show()

    # ── Load factions ─────────────────────────────────────

    def _load_factions(self):
        self._status_lbl.setText("Loading...")
        self._new_btn.setEnabled(False)
        uid          = self._uni_combo.currentData()
        canon_filter = self._canon_combo.currentData()
        name_filter  = self._search_input.text().strip()
        self._load_worker = LoadFactionsWorker(uid, canon_filter, name_filter)
        self._load_worker.done.connect(self._on_loaded)
        self._load_worker.error.connect(self._on_error)
        self._load_worker.start()

    def _on_search_changed(self, text: str):
        if len(text) == 0 or len(text) >= 2:
            self._load_factions()

    def _on_loaded(self, factions: list):
        self._factions = factions
        self._rebuild_cards()
        count = len(factions)
        self._status_lbl.setText(f"{count} faction{'s' if count != 1 else ''}")
        self._new_btn.setEnabled(True)

    def _on_error(self, msg: str):
        self._status_lbl.setText(f"Error: {msg}")
        self._new_btn.setEnabled(True)

    # ── Card grid ─────────────────────────────────────────

    def _rebuild_cards(self):
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._factions:
            empty = QLabel("Koi faction nahi mili.\n\nUpar '＋ New Faction' click karein.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color: #222; font-size: 16px; padding: 60px; "
                "background: transparent; border: none;"
            )
            self._cards_layout.addWidget(empty, 0, 0, 1, 3)
            return

        cols = 3
        for i, data in enumerate(self._factions):
            card = FactionCard(data)
            card.edit_clicked.connect(self._open_edit)
            card.delete_clicked.connect(self._confirm_delete)
            self._cards_layout.addWidget(card, i // cols, i % cols)

        remainder = len(self._factions) % cols
        if remainder:
            for j in range(cols - remainder):
                spacer = QWidget()
                spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                row = len(self._factions) // cols
                self._cards_layout.addWidget(spacer, row, remainder + j)

    # ── Delete ────────────────────────────────────────────

    def _confirm_delete(self, data: dict):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete Faction")
        dlg.setText(
            f"<b style='color:#e74c3c'>'{data['name']}'</b> delete karna chahte ho?<br>"
            "<small style='color:#666'>Yeh action undo nahi hogi.</small>"
        )
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        dlg.setDefaultButton(QMessageBox.Cancel)
        dlg.setStyleSheet("""
            QMessageBox { background: #111; color: #CCC; font-size: 13px; }
            QPushButton {
                background: #1A1A1A; color: #CCC;
                border: 1px solid #333; border-radius: 6px;
                padding: 6px 20px; font-size: 13px;
            }
            QPushButton:hover { background: #222; }
        """)

        if dlg.exec() == QMessageBox.Yes:
            self._delete_worker = DeleteFactionWorker(data["id"])
            self._delete_worker.done.connect(lambda _: self._load_factions())
            self._delete_worker.error.connect(self._on_error)
            self._delete_worker.start()
