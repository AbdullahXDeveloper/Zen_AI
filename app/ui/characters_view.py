"""
app/ui/characters_view.py
Zen AI — Characters CRUD Page (Phase 9C)

Features:
  - Card grid: all characters, color-coded by canon_status
  - Filter bar: universe, canon_status, search by name
  - Slide-in right panel: Create / Edit form (all fields, scrollable)
  - Delete confirmation dialog
  - QThread workers for non-blocking DB ops

Fixes (v2):
  - Form panel has fixed header (✕ close) + fixed footer (Cancel/Save)
  - Panel closes itself immediately on save/cancel
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
    "canon":        "#00ADB5",
    "non_canon":    "#e74c3c",
    "alt_timeline": "#9b59b6",
    "experimental": "#f39c12",
}
CANON_OPTIONS = ["canon", "non_canon", "alt_timeline", "experimental"]


# ─────────────────────────────────────────────────────────
# Workers
# ─────────────────────────────────────────────────────────
class LoadCharactersWorker(QThread):
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
            chars = crud.list_characters(
                session,
                universe_id=self.universe_id,
                canon_status=self.canon_filter or None,
                name_contains=self.name_filter or None,
            )
            result = [
                {
                    "id":               c.id,
                    "name":             c.name,
                    "species":          c.species or "—",
                    "titles":           c.titles or "",
                    "aliases":          c.aliases or "",
                    "personality":      c.personality or "",
                    "motivations":      c.motivations or "",
                    "goals":            c.goals or "",
                    "ideology":         c.ideology or "",
                    "traits_json":      c.traits_json or {},
                    "canon_status":     c.canon_status,
                    "importance_score": c.importance_score,
                    "universe_id":      c.universe_id,
                    "universe_name":    c.universe.name if c.universe else "—",
                    "faction_id":       c.faction_id,
                    "root_entity_id":   c.root_entity_id,
                }
                for c in chars
            ]
            session.close()
            self.done.emit(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals(): session.close()


class LoadDependenciesForCharWorker(QThread):
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
            if 'session' in locals(): session.close()


class SaveCharacterWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, data: dict, character_id: int = None):
        super().__init__()
        self.data         = data
        self.character_id = character_id

    def run(self):
        try:
            session = get_session()
            if self.character_id:
                crud.update_character(session, self.character_id, **self.data)
            else:
                crud.create_character(session, **self.data)
            session.close()
            self.done.emit("ok")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals(): session.close()


class DeleteCharacterWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, character_id: int):
        super().__init__()
        self.character_id = character_id

    def run(self):
        try:
            session = get_session()
            crud.delete_character(session, self.character_id)
            session.close()
            self.done.emit("ok")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals(): session.close()


# ─────────────────────────────────────────────────────────
# Character Card
# ─────────────────────────────────────────────────────────
class CharacterCard(QFrame):
    edit_clicked   = Signal(dict)
    delete_clicked = Signal(dict)

    def __init__(self, data: dict):
        super().__init__()
        self.data  = data
        color = CANON_COLORS.get(data["canon_status"], "#00ADB5")

        self.setFixedHeight(180)
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
        lay.setSpacing(5)

        # ── Header row ──
        hdr = QHBoxLayout()
        name_lbl = QLabel(f"👤  {data['name']}")
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

        # ── Species + Universe ──
        meta_row = QHBoxLayout()
        species_lbl = QLabel(f"🧬 {data['species']}")
        species_lbl.setStyleSheet(
            "color: #555; font-size: 11px; background: transparent; border: none;"
        )
        uni_lbl = QLabel(f"🌐 {data['universe_name']}")
        uni_lbl.setStyleSheet(
            "color: #444; font-size: 11px; background: transparent; border: none;"
        )
        meta_row.addWidget(species_lbl)
        meta_row.addSpacing(14)
        meta_row.addWidget(uni_lbl)
        meta_row.addStretch()
        lay.addLayout(meta_row)

        # ── Trait pills (top 3) ──
        traits = data.get("traits_json") or {}
        if traits:
            top_traits = sorted(traits.items(), key=lambda x: x[1], reverse=True)[:3]
            trait_row = QHBoxLayout()
            trait_row.setSpacing(6)
            for t_name, val in top_traits:
                pill = QLabel(f"{t_name} {val}")
                pill.setStyleSheet(
                    f"color: {color}; font-size: 9px; font-weight: 600; "
                    f"background: {color}12; border: 1px solid {color}33; "
                    "border-radius: 3px; padding: 1px 7px;"
                )
                trait_row.addWidget(pill)
            trait_row.addStretch()
            lay.addLayout(trait_row)
        else:
            lay.addSpacing(4)

        # ── Personality snippet ──
        personality = data.get("personality", "")
        if personality:
            snippet = (personality[:80] + "…") if len(personality) > 80 else personality
            p_lbl = QLabel(snippet)
            p_lbl.setWordWrap(True)
            p_lbl.setStyleSheet(
                "color: #404040; font-size: 11px; background: transparent; border: none;"
            )
            lay.addWidget(p_lbl)
        else:
            lay.addStretch()

        lay.addStretch()

        # ── Footer ──
        foot = QHBoxLayout()
        score_lbl = QLabel(f"★ {data['importance_score']}")
        score_lbl.setStyleSheet(
            f"color: {color}88; font-size: 11px; background: transparent; border: none;"
        )
        edit_btn = QPushButton("✎  Edit")
        edit_btn.setFixedSize(70, 26)
        edit_btn.setStyleSheet(self._action_btn("#00ADB5"))
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
# Slide-in Form Panel  (FIXED: header + footer always visible)
# ─────────────────────────────────────────────────────────
class CharacterFormPanel(QFrame):
    """Right-side slide-in panel for Create / Edit."""
    saved     = Signal()
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._edit_id       = None
        self._worker        = None
        self._universes     = []
        self._factions      = []
        self._root_entities = []

        self.setFixedWidth(400)
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

        self._title = QLabel("New Character")
        self._title.setStyleSheet(
            "color: #9b59b6; font-size: 15px; font-weight: 800; "
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
        self._save_btn.setStyleSheet("""
            QPushButton {
                background: #9b59b6; color: #FFF;
                border: none; border-radius: 5px;
                font-size: 12px; font-weight: 700;
            }
            QPushButton:hover { background: #a96cc7; }
            QPushButton:disabled { background: #2A1A3A; color: #555; }
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

        fs = """
            QLineEdit, QTextEdit, QComboBox {
                background: #0D0D0D; color: #CCCCCC;
                border: 1px solid #222; border-radius: 6px;
                padding: 7px 12px; font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color: #9b59b6; }
            QComboBox QAbstractItemView {
                background: #111; color: #CCC;
                selection-background-color: #9b59b6;
            }
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
        lay.addWidget(_lbl("NAME  *"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g.  Raven")
        self.name_input.setStyleSheet(fs)
        lay.addWidget(self.name_input)

        # Species
        lay.addWidget(_lbl("SPECIES"))
        self.species_input = QLineEdit()
        self.species_input.setPlaceholderText("e.g.  Human, Hybrid, Unknown")
        self.species_input.setStyleSheet(fs)
        lay.addWidget(self.species_input)

        # Titles
        lay.addWidget(_lbl("TITLES"))
        self.titles_input = QLineEdit()
        self.titles_input.setPlaceholderText("e.g.  The Shadow, Lord of War")
        self.titles_input.setStyleSheet(fs)
        lay.addWidget(self.titles_input)

        # Aliases
        lay.addWidget(_lbl("ALIASES"))
        self.aliases_input = QLineEdit()
        self.aliases_input.setPlaceholderText("e.g.  The Black One, X-7")
        self.aliases_input.setStyleSheet(fs)
        lay.addWidget(self.aliases_input)

        # Personality
        lay.addWidget(_lbl("PERSONALITY"))
        self.personality_input = QTextEdit()
        self.personality_input.setPlaceholderText("Character ki personality...")
        self.personality_input.setFixedHeight(68)
        self.personality_input.setStyleSheet(fs)
        lay.addWidget(self.personality_input)

        # Motivations
        lay.addWidget(_lbl("MOTIVATIONS"))
        self.motivations_input = QTextEdit()
        self.motivations_input.setPlaceholderText("Character kya chahta hai?")
        self.motivations_input.setFixedHeight(56)
        self.motivations_input.setStyleSheet(fs)
        lay.addWidget(self.motivations_input)

        # Goals
        lay.addWidget(_lbl("GOALS"))
        self.goals_input = QTextEdit()
        self.goals_input.setPlaceholderText("Long-term goals...")
        self.goals_input.setFixedHeight(56)
        self.goals_input.setStyleSheet(fs)
        lay.addWidget(self.goals_input)

        # Ideology
        lay.addWidget(_lbl("IDEOLOGY"))
        self.ideology_input = QTextEdit()
        self.ideology_input.setPlaceholderText("Beliefs / worldview...")
        self.ideology_input.setFixedHeight(56)
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
        self.score_slider.setStyleSheet("""
            QSlider::groove:horizontal { background: #1A1A1A; height: 6px; border-radius: 3px; }
            QSlider::handle:horizontal { background: #9b59b6; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }
            QSlider::sub-page:horizontal { background: #9b59b6; border-radius: 3px; }
        """)
        self.score_val = QLabel("50")
        self.score_val.setFixedWidth(30)
        self.score_val.setStyleSheet(
            "color: #9b59b6; font-size: 13px; font-weight: 700; background: transparent; border: none;"
        )
        self.score_slider.valueChanged.connect(lambda v: self.score_val.setText(str(v)))
        score_row.addWidget(self.score_slider)
        score_row.addWidget(self.score_val)
        lay.addLayout(score_row)

        # Story Links
        lay.addSpacing(8)
        self.story_links = EntityLinksWidget("character")
        lay.addWidget(self.story_links)

        lay.addStretch()

        scroll.setWidget(fw)
        main.addWidget(scroll)

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

    # ── Dependencies dropdown ──────────────────────────────────

    def set_dependencies(self, deps: dict):
        self._universes = deps.get("universes", [])
        self.universe_combo.clear()
        self.universe_combo.addItem("None", None)
        for u in self._universes:
            self.universe_combo.addItem(u["name"], u["id"])
            
        self._factions = deps.get("factions", [])
        self.faction_combo.clear()
        self.faction_combo.addItem("None", None)
        for f in self._factions:
            self.faction_combo.addItem(f["name"], f["id"])
            
        self._root_entities = deps.get("root_entities", [])
        self.root_entity_combo.clear()
        self.root_entity_combo.addItem("None", None)
        for r in self._root_entities:
            self.root_entity_combo.addItem(r["name"], r["id"])

    # ── Public API ─────────────────────────────────────────

    def open_create(self):
        self._edit_id = None
        self._title.setText("New Character")
        self._clear_fields()
        self._status.setText("")
        self._save_btn.setEnabled(True)
        self.story_links.set_pending_entity()

    def open_edit(self, data: dict):
        self._edit_id = data["id"]
        self._title.setText("Edit Character")
        self._status.setText("")
        self._save_btn.setEnabled(True)

        self.universe_combo.blockSignals(True)
        self.faction_combo.blockSignals(True)
        self.root_entity_combo.blockSignals(True)

        self.universe_combo.setCurrentIndex(0)
        for i in range(self.universe_combo.count()):
            if self.universe_combo.itemData(i) == data.get("universe_id"):
                self.universe_combo.setCurrentIndex(i)
                break
                
        self.faction_combo.setCurrentIndex(0)
        for i in range(self.faction_combo.count()):
            if self.faction_combo.itemData(i) == data.get("faction_id"):
                self.faction_combo.setCurrentIndex(i)
                break

        self.root_entity_combo.setCurrentIndex(0)
        for i in range(self.root_entity_combo.count()):
            if self.root_entity_combo.itemData(i) == data.get("root_entity_id"):
                self.root_entity_combo.setCurrentIndex(i)
                break

        self.universe_combo.blockSignals(False)
        self.faction_combo.blockSignals(False)
        self.root_entity_combo.blockSignals(False)
        
        self._update_visibility()

        self.name_input.setText(data["name"])
        self.species_input.setText("" if data["species"] == "—" else data["species"])
        self.titles_input.setText(data["titles"])
        self.aliases_input.setText(data["aliases"])
        self.personality_input.setPlainText(data["personality"])
        self.motivations_input.setPlainText(data["motivations"])
        self.goals_input.setPlainText(data["goals"])
        self.ideology_input.setPlainText(data["ideology"])
        idx = CANON_OPTIONS.index(data["canon_status"]) if data["canon_status"] in CANON_OPTIONS else 0
        self.canon_combo.setCurrentIndex(idx)
        self.score_slider.setValue(data["importance_score"])
        self.story_links.load_for_entity(data["id"])

    # ── Internal ───────────────────────────────────────────

    def _clear_fields(self):
        self.name_input.clear()
        self.species_input.clear()
        self.titles_input.clear()
        self.aliases_input.clear()
        self.personality_input.clear()
        self.motivations_input.clear()
        self.goals_input.clear()
        self.ideology_input.clear()
        self.canon_combo.setCurrentIndex(0)
        self.score_slider.setValue(50)
        
        self.universe_combo.blockSignals(True)
        self.faction_combo.blockSignals(True)
        self.root_entity_combo.blockSignals(True)
        
        if self.universe_combo.count():
            self.universe_combo.setCurrentIndex(0)
        if self.faction_combo.count():
            self.faction_combo.setCurrentIndex(0)
        if self.root_entity_combo.count():
            self.root_entity_combo.setCurrentIndex(0)
            
        self.universe_combo.blockSignals(False)
        self.faction_combo.blockSignals(False)
        self.root_entity_combo.blockSignals(False)
        
        self._update_visibility()

    def _cancel(self):
        """Close immediately."""
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

        selected_count = sum(1 for x in [uid, fid, rid] if x is not None)
        if selected_count != 1:
            self._status.setText("⚠  Select exactly ONE connection (Universe, Faction, or Root Entity)!")
            return

        payload = {
            "universe_id":      uid,
            "name":             name,
            "species":          self.species_input.text().strip() or None,
            "titles":           self.titles_input.text().strip() or None,
            "aliases":          self.aliases_input.text().strip() or None,
            "personality":      self.personality_input.toPlainText().strip() or None,
            "motivations":      self.motivations_input.toPlainText().strip() or None,
            "goals":            self.goals_input.toPlainText().strip() or None,
            "ideology":         self.ideology_input.toPlainText().strip() or None,
            "canon_status":     self.canon_combo.currentData(),
            "importance_score": self.score_slider.value(),
            "faction_id":       self.faction_combo.currentData(),
            "root_entity_id":   self.root_entity_combo.currentData(),
        }

        self._save_btn.setEnabled(False)
        self._status.setText("Saving...")
        self._status.setStyleSheet(
            "color: #9b59b6; font-size: 11px; background: transparent; border: none;"
        )

        self._worker = SaveCharacterWorker(payload, self._edit_id)
        self._worker.done.connect(self._on_saved)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_saved(self, _):
        self.hide()                 # close immediately
        self._save_btn.setEnabled(True)
        self._status.setText("")
        self.saved.emit()           # parent reloads cards

    def _on_error(self, msg: str):
        self._status.setText(f"⚠  {msg}")
        self._status.setStyleSheet(
            "color: #e74c3c; font-size: 11px; background: transparent; border: none;"
        )
        self._save_btn.setEnabled(True)


# ─────────────────────────────────────────────────────────
# Main Characters View
# ─────────────────────────────────────────────────────────
class CharactersViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._load_worker   = None
        self._dep_worker    = None
        self._delete_worker = None
        self._characters    = []
        self._universes     = []
        self._setup_ui()
        self._load_dependencies()

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

        title = QLabel("👤  Characters")
        title.setStyleSheet(
            "color: #9b59b6; font-size: 20px; font-weight: 900; "
            "letter-spacing: 2px; background: transparent; border: none;"
        )
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(
            "color: #333; font-size: 11px; background: transparent; border: none;"
        )

        self._new_btn = QPushButton("＋  New Character")
        self._new_btn.setFixedHeight(34)
        self._new_btn.setStyleSheet("""
            QPushButton {
                background: #9b59b6; color: #FFF;
                border: none; border-radius: 7px;
                padding: 0 18px; font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background: #a96cc7; }
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
        self._search_input.setPlaceholderText("🔍  Search characters...")
        self._search_input.setFixedHeight(30)
        self._search_input.setFixedWidth(220)
        self._search_input.setStyleSheet("""
            QLineEdit {
                background: #111; color: #CCC;
                border: 1px solid #222; border-radius: 6px;
                padding: 0 12px; font-size: 12px;
            }
            QLineEdit:focus { border-color: #9b59b6; }
        """)
        self._search_input.textChanged.connect(self._on_search_changed)

        combo_style = """
            QComboBox {
                background: #111; color: #888;
                border: 1px solid #222; border-radius: 6px;
                padding: 0 10px; font-size: 12px;
                min-width: 140px; height: 30px;
            }
            QComboBox:hover { border-color: #333; }
            QComboBox QAbstractItemView {
                background: #111; color: #CCC;
                selection-background-color: #9b59b6;
            }
        """

        self._uni_combo = QComboBox()
        self._uni_combo.addItem("All Universes", None)
        self._uni_combo.setStyleSheet(combo_style)
        self._uni_combo.currentIndexChanged.connect(self._load_characters)

        self._canon_combo = QComboBox()
        self._canon_combo.addItem("All Canon Status", None)
        for opt in CANON_OPTIONS:
            self._canon_combo.addItem(opt.replace("_", " ").title(), opt)
        self._canon_combo.setStyleSheet(combo_style)
        self._canon_combo.currentIndexChanged.connect(self._load_characters)

        f_lay.addWidget(self._search_input)
        f_lay.addWidget(self._uni_combo)
        f_lay.addWidget(self._canon_combo)
        f_lay.addStretch()
        left_lay.addWidget(filter_bar)

        # ── Cards scroll area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: #0D0D0D; }
            QScrollBar:vertical { background: #111; width: 6px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: #2A2A2A; border-radius: 3px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #9b59b6; }
        """)

        self._cards_widget = QWidget()
        self._cards_widget.setStyleSheet("background: #0D0D0D;")
        self._cards_layout = QGridLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(32, 24, 32, 32)
        self._cards_layout.setSpacing(16)
        self._cards_layout.setAlignment(Qt.AlignTop)

        self._scroll.setWidget(self._cards_widget)
        left_lay.addWidget(self._scroll)

        root.addWidget(main_area, 1)   # stretch=1 so main area takes all remaining space

        # ── Right: Slide-in form panel ──
        self._form_panel = CharacterFormPanel()
        self._form_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._form_panel.saved.connect(self._load_characters)
        self._form_panel.cancelled.connect(self._load_characters)
        self._form_panel.hide()
        root.addWidget(self._form_panel, 0)   # stretch=0 so panel is only as wide as needed

    def showEvent(self, event):
        super().showEvent(event)
        # Refresh dependencies every time tab is opened
        self._load_dependencies()

    # ── Dependencies loading ───────────────────────────────────

    def _load_dependencies(self):
        self._dep_worker = LoadDependenciesForCharWorker()
        self._dep_worker.done.connect(self._on_dependencies_loaded)
        self._dep_worker.error.connect(lambda _: self._load_characters())
        self._dep_worker.start()

    def _on_dependencies_loaded(self, deps: dict):
        self._universes = deps.get("universes", [])

        self._uni_combo.blockSignals(True)
        self._uni_combo.clear()
        self._uni_combo.addItem("All Universes", None)
        for u in self._universes:
            self._uni_combo.addItem(u["name"], u["id"])
        self._uni_combo.blockSignals(False)

        self._form_panel.set_dependencies(deps)
        self._load_characters()

    # ── Panel open/close ──────────────────────────────────

    def _open_create(self):
        self._form_panel.open_create()
        self._form_panel.show()

    def _open_edit(self, data: dict):
        self._form_panel.open_edit(data)
        self._form_panel.show()

    # ── Load characters ───────────────────────────────────

    def _load_characters(self):
        self._status_lbl.setText("Loading...")
        self._new_btn.setEnabled(False)
        uid          = self._uni_combo.currentData()
        canon_filter = self._canon_combo.currentData()
        name_filter  = self._search_input.text().strip()
        self._load_worker = LoadCharactersWorker(uid, canon_filter, name_filter)
        self._load_worker.done.connect(self._on_loaded)
        self._load_worker.error.connect(self._on_error)
        self._load_worker.start()

    def _on_search_changed(self, text: str):
        if len(text) == 0 or len(text) >= 2:
            self._load_characters()

    def _on_loaded(self, characters: list):
        self._characters = characters
        self._rebuild_cards()
        count = len(characters)
        self._status_lbl.setText(f"{count} character{'s' if count != 1 else ''}")
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

        if not self._characters:
            empty = QLabel("Koi character nahi mila.\n\nUpar '＋ New Character' click karein.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color: #222; font-size: 16px; padding: 60px; "
                "background: transparent; border: none;"
            )
            self._cards_layout.addWidget(empty, 0, 0, 1, 3)
            return

        cols = 3
        for i, data in enumerate(self._characters):
            card = CharacterCard(data)
            card.edit_clicked.connect(self._open_edit)
            card.delete_clicked.connect(self._confirm_delete)
            self._cards_layout.addWidget(card, i // cols, i % cols)

        remainder = len(self._characters) % cols
        if remainder:
            for j in range(cols - remainder):
                spacer = QWidget()
                spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                row = len(self._characters) // cols
                self._cards_layout.addWidget(spacer, row, remainder + j)

    # ── Delete ────────────────────────────────────────────

    def _confirm_delete(self, data: dict):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete Character")
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
            self._delete_worker = DeleteCharacterWorker(data["id"])
            self._delete_worker.done.connect(lambda _: self._load_characters())
            self._delete_worker.error.connect(self._on_error)
            self._delete_worker.start()
