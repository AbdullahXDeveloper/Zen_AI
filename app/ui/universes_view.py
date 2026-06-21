"""
app/ui/universes_view.py
Zen AI — Universes CRUD Page (Phase 9B)

Features:
  - Card grid: all universes, color-coded by canon_status
  - Filter bar: canon_status, search by name
  - Slide-in right panel: Create / Edit form
  - Delete confirmation dialog
  - QThread workers for non-blocking DB ops
  - Universe Cosmic Tree: hierarchical node browser per universe
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QLineEdit, QComboBox,
    QTextEdit, QSlider, QDialog, QDialogButtonBox,
    QGridLayout, QSizePolicy, QMessageBox, QSpacerItem,
    QTreeWidget, QTreeWidgetItem, QMenu, QStackedWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont, QIntValidator, QIcon

from app.database.db_init import get_session
from app.database import crud
from app.database.models import NODE_TYPES, NODE_ICONS
from app.utils.dashboard_generator import generate_entity_dashboard

# ─────────────────────────────────────────────────────────
# Canon status colours
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
class LoadUniversesWorker(QThread):
    done  = Signal(list)
    error = Signal(str)

    def __init__(self, canon_filter=None, name_filter=None):
        super().__init__()
        self.canon_filter = canon_filter
        self.name_filter  = name_filter

    def run(self):
        try:
            session = get_session()
            unis = crud.list_universes(
                session,
                canon_status=self.canon_filter or None,
                name_contains=self.name_filter or None,
            )
            result = []
            for u in unis:
                links = crud.list_root_entity_links(session, entity_type="universe", entity_id=u.id)
                root_entity_id = links[0].root_entity_id if links else None
                result.append({
                    "id":          u.id,
                    "name":        u.name,
                    "description": u.description or "",
                    "canon_status": u.canon_status,
                    "importance_score": u.importance_score,
                    "root_entity_id": root_entity_id,
                })
            
            # Also fetch root entities for the dropdown
            root_entities = crud.list_root_entities(session)
            root_entities_data = [{"id": re.id, "name": re.name} for re in root_entities]
            
            session.close()
            self.done.emit([result, root_entities_data])
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class SaveUniverseWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, data: dict, universe_id: int = None):
        super().__init__()
        self.data        = data
        self.universe_id = universe_id

    def run(self):
        try:
            session = get_session()
            root_entity_id = self.data.pop("root_entity_id", None)
            
            if self.universe_id:
                crud.update_universe(session, self.universe_id, **self.data)
                uid = self.universe_id
            else:
                uni = crud.create_universe(session, **self.data)
                uid = uni.id
                
            # Handle root entity link
            existing_links = crud.list_root_entity_links(session, entity_type="universe", entity_id=uid)
            for link in existing_links:
                crud.delete_root_entity_link(session, link.id)
                
            if root_entity_id:
                crud.create_root_entity_link(session, root_entity_id=root_entity_id, entity_type="universe", entity_id=uid)
                
            session.commit()
            generate_entity_dashboard()
            self.done.emit("ok")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class DeleteUniverseWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, universe_id: int):
        super().__init__()
        self.universe_id = universe_id

    def run(self):
        try:
            session = get_session()
            # Clean up RootEntityLinks FIRST to prevent stale ghost links
            existing_links = crud.list_root_entity_links(session, entity_type="universe", entity_id=self.universe_id)
            for link in existing_links:
                crud.delete_root_entity_link(session, link.id)
            crud.delete_universe(session, self.universe_id)
            session.commit()
            generate_entity_dashboard()
            self.done.emit("ok")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


# ─────────────────────────────────────────────────────────
# Universe Card
# ─────────────────────────────────────────────────────────
class UniverseCard(QFrame):
    edit_clicked   = Signal(dict)
    delete_clicked = Signal(dict)
    tree_clicked   = Signal(dict)  # new — opens cosmic tree for this universe

    def __init__(self, data: dict):
        super().__init__()
        self.data  = data
        color = CANON_COLORS.get(data["canon_status"], "#00ADB5")

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

        name_lbl = QLabel(f"🌐  {data['name']}")
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

        # ── Description ──
        desc = data["description"][:90] + "…" if len(data["description"]) > 90 else data["description"]
        desc_lbl = QLabel(desc or "No description.")
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(
            "color: #555; font-size: 12px; background: transparent; border: none;"
        )
        lay.addWidget(desc_lbl)

        lay.addStretch()

        # ── Footer row ──
        foot = QHBoxLayout()
        score_lbl = QLabel(f"★ Importance: {data['importance_score']}")
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

        tree_btn = QPushButton("🌳  Tree")
        tree_btn.setFixedSize(80, 26)
        tree_btn.setStyleSheet(self._action_btn("#2ecc71"))
        tree_btn.clicked.connect(lambda: self.tree_clicked.emit(self.data))

        foot.addWidget(tree_btn)
        foot.addSpacing(6)
        foot.addWidget(edit_btn)
        foot.addSpacing(6)
        foot.addWidget(del_btn)
        lay.addLayout(foot)

    @staticmethod
    def _action_btn(color: str) -> str:
        return f"""
            QPushButton {{
                background: transparent;
                color: {color};
                border: 1px solid {color}44;
                border-radius: 5px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {color}18;
                border-color: {color};
            }}
        """


# ─────────────────────────────────────────────────────────
# Slide-in Form Panel  (FIXED: header + footer always visible)
# ─────────────────────────────────────────────────────────
class UniverseFormPanel(QFrame):
    """Right-side slide-in panel for Create / Edit."""
    saved     = Signal()
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._edit_id = None
        self._worker  = None

        self.setFixedWidth(380)
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

        self._title = QLabel("New Universe")
        self._title.setStyleSheet(
            "color: #00ADB5; font-size: 15px; font-weight: 800; "
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
                background: #00ADB5; color: #000;
                border: none; border-radius: 5px;
                font-size: 12px; font-weight: 700;
            }
            QPushButton:hover { background: #00C9D4; }
            QPushButton:disabled { background: #1A3A3A; color: #555; }
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
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

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
                padding: 8px 12px; font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color: #00ADB5; }
            QComboBox QAbstractItemView {
                background: #111; color: #CCC;
                selection-background-color: #00ADB5;
            }
        """

        lay.addWidget(_lbl("NAME  *"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g.  Zendrix Prime")
        self.name_input.setStyleSheet(fs)
        lay.addWidget(self.name_input)

        lay.addWidget(_lbl("DESCRIPTION"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Universe ka brief description...")
        self.desc_input.setFixedHeight(110)
        self.desc_input.setStyleSheet(fs)
        lay.addWidget(self.desc_input)

        lay.addWidget(_lbl("CANON STATUS"))
        self.canon_combo = QComboBox()
        for opt in CANON_OPTIONS:
            self.canon_combo.addItem(opt.replace("_", " ").title(), opt)
        self.canon_combo.setStyleSheet(fs)
        lay.addWidget(self.canon_combo)

        lay.addWidget(_lbl("LINKED ROOT ENTITY"))
        self.root_combo = QComboBox()
        self.root_combo.addItem("None", None)
        self.root_combo.setStyleSheet(fs)
        lay.addWidget(self.root_combo)

        lay.addWidget(_lbl("IMPORTANCE SCORE  (1 – 100)"))
        score_row = QHBoxLayout()
        self.score_slider = QSlider(Qt.Horizontal)
        self.score_slider.setRange(1, 100)
        self.score_slider.setValue(50)
        self.score_slider.setStyleSheet("""
            QSlider::groove:horizontal { background: #1A1A1A; height: 6px; border-radius: 3px; }
            QSlider::handle:horizontal { background: #00ADB5; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }
            QSlider::sub-page:horizontal { background: #00ADB5; border-radius: 3px; }
        """)
        self.score_val = QLabel("50")
        self.score_val.setFixedWidth(30)
        self.score_val.setStyleSheet(
            "color: #00ADB5; font-size: 13px; font-weight: 700; background: transparent; border: none;"
        )
        self.score_slider.valueChanged.connect(lambda v: self.score_val.setText(str(v)))
        score_row.addWidget(self.score_slider)
        score_row.addWidget(self.score_val)
        lay.addLayout(score_row)
        lay.addStretch()

        scroll.setWidget(fw)
        main.addWidget(scroll)


    # ── Public API ────────────────────────────────────────

    def open_create(self):
        self._edit_id = None
        self._title.setText("New Universe")
        self.name_input.clear()
        self.desc_input.clear()
        self.canon_combo.setCurrentIndex(0)
        self.root_combo.setCurrentIndex(0)
        self.score_slider.setValue(50)
        self._status.setText("")
        self._save_btn.setEnabled(True)

    def open_edit(self, data: dict):
        self._edit_id = data["id"]
        self._title.setText("Edit Universe")
        self.name_input.setText(data["name"])
        self.desc_input.setPlainText(data["description"])
        idx = CANON_OPTIONS.index(data["canon_status"]) if data["canon_status"] in CANON_OPTIONS else 0
        self.canon_combo.setCurrentIndex(idx)
        
        # Set root entity combo
        root_id = data.get("root_entity_id")
        idx = self.root_combo.findData(root_id) if root_id else 0
        self.root_combo.setCurrentIndex(idx if idx >= 0 else 0)
        
        self.score_slider.setValue(data["importance_score"])
        self._status.setText("")
        self._save_btn.setEnabled(True)

    # ── Internal ──────────────────────────────────────────

    def _cancel(self):
        """Close immediately — no signal chain delay."""
        self.hide()
        self.cancelled.emit()

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            self._status.setText("⚠  Name required!")
            return

        payload = {
            "name":             name,
            "description":      self.desc_input.toPlainText().strip(),
            "canon_status":     self.canon_combo.currentData(),
            "importance_score": self.score_slider.value(),
            "root_entity_id":   self.root_combo.currentData(),
        }

        self._save_btn.setEnabled(False)
        self._status.setText("Saving...")
        self._status.setStyleSheet(
            "color: #00ADB5; font-size: 11px; background: transparent; border: none;"
        )

        self._worker = SaveUniverseWorker(payload, self._edit_id)
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
# Cosmic Tree — Workers
# ─────────────────────────────────────────────────────────
class LoadTreeWorker(QThread):
    done  = Signal(list)
    error = Signal(str)

    def __init__(self, universe_id: int):
        super().__init__()
        self.universe_id = universe_id

    def run(self):
        try:
            session = get_session()
            nodes = crud.list_cosmic_nodes_by_universe(session, self.universe_id)
            result = [
                {
                    "id":               n.id,
                    "name":             n.name,
                    "node_type":        n.node_type,
                    "description":      n.description or "",
                    "importance_score": n.importance_score,
                    "parent_id":        n.parent_id,
                    "universe_id":      n.universe_id,
                }
                for n in nodes
            ]
            session.close()
            self.done.emit(result)
        except Exception as e:
            import traceback; traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class SaveNodeWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, data: dict, node_id: int = None):
        super().__init__()
        self.data    = data
        self.node_id = node_id

    def run(self):
        try:
            session = get_session()
            if self.node_id:
                crud.update_cosmic_node(session, self.node_id, **self.data)
            else:
                crud.create_cosmic_node(session, **self.data)
            session.close()
            self.done.emit("ok")
        except Exception as e:
            import traceback; traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class DeleteNodeWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, node_id: int):
        super().__init__()
        self.node_id = node_id

    def run(self):
        try:
            session = get_session()
            crud.delete_cosmic_node(session, self.node_id)
            session.close()
            self.done.emit("ok")
        except Exception as e:
            import traceback; traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


# ─────────────────────────────────────────────────────────
# Node Form Panel (slide-in right panel for tree)
# ─────────────────────────────────────────────────────────
class NodeFormPanel(QFrame):
    saved     = Signal()
    cancelled = Signal()

    def __init__(self, universe_id: int, parent=None):
        super().__init__(parent)
        self._universe_id = universe_id
        self._edit_id     = None
        self._parent_id   = None
        self._worker      = None

        self.setFixedWidth(360)
        self.setStyleSheet("QFrame { background: #111111; border-left: 1px solid #1E1E1E; }")

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet("background: #111111; border-bottom: 1px solid #1E1E1E;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(18, 0, 10, 0)
        h_lay.setSpacing(8)

        self._title = QLabel("New Node")
        self._title.setStyleSheet(
            "color: #2ecc71; font-size: 14px; font-weight: 800; "
            "background: transparent; border: none;"
        )
        self._status = QLabel("")
        self._status.setStyleSheet(
            "color: #e74c3c; font-size: 10px; background: transparent; border: none;"
        )

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedSize(60, 28)
        self._cancel_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #666;
                border: 1px solid #333; border-radius: 5px; font-size: 11px; }
            QPushButton:hover { color: #AAA; border-color: #555; }
        """)
        self._cancel_btn.clicked.connect(self._cancel)

        self._save_btn = QPushButton("✓  Save")
        self._save_btn.setFixedSize(78, 28)
        self._save_btn.setStyleSheet("""
            QPushButton { background: #2ecc71; color: #000;
                border: none; border-radius: 5px; font-size: 11px; font-weight: 700; }
            QPushButton:hover { background: #3de382; }
            QPushButton:disabled { background: #0A2A1A; color: #555; }
        """)
        self._save_btn.clicked.connect(self._save)

        x_btn = QPushButton("✕")
        x_btn.setFixedSize(26, 26)
        x_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #444;
                border: none; font-size: 13px; border-radius: 4px; }
            QPushButton:hover { color: #e74c3c; background: #1A1A1A; }
        """)
        x_btn.clicked.connect(self._cancel)

        h_lay.addWidget(self._title)
        h_lay.addStretch()
        h_lay.addWidget(self._status)
        h_lay.addWidget(self._cancel_btn)
        h_lay.addWidget(self._save_btn)
        h_lay.addSpacing(2)
        h_lay.addWidget(x_btn)
        main.addWidget(header)

        # Scrollable fields
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
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        def _lbl(t):
            l = QLabel(t)
            l.setStyleSheet(
                "color: #444; font-size: 10px; font-weight: 700; "
                "letter-spacing: 1px; background: transparent; border: none;"
            )
            return l

        fs = """
            QLineEdit, QTextEdit, QComboBox {
                background: #0D0D0D; color: #CCC;
                border: 1px solid #222; border-radius: 6px;
                padding: 7px 10px; font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color: #2ecc71; }
            QComboBox QAbstractItemView {
                background: #111; color: #CCC;
                selection-background-color: #2ecc71;
            }
        """

        # Parent info (read-only label)
        self._parent_lbl = QLabel("")
        self._parent_lbl.setStyleSheet(
            "color: #2ecc71; font-size: 10px; background: #0A2A1A; "
            "border: 1px solid #2ecc7144; border-radius: 5px; "
            "padding: 4px 10px;"
        )
        self._parent_lbl.setVisible(False)
        lay.addWidget(self._parent_lbl)

        lay.addWidget(_lbl("NAME  *"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Black Hole Z_1, Galaxy Andromeda")
        self.name_input.setStyleSheet(fs)
        lay.addWidget(self.name_input)

        lay.addWidget(_lbl("NODE TYPE"))
        self.type_combo = QComboBox()
        for nt in NODE_TYPES:
            icon = NODE_ICONS.get(nt, "📦")
            self.type_combo.addItem(f"{icon}  {nt.replace('_', ' ').title()}", nt)
        self.type_combo.setStyleSheet(fs)
        lay.addWidget(self.type_combo)

        lay.addWidget(_lbl("DESCRIPTION"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Optional notes about this cosmic entity...")
        self.desc_input.setFixedHeight(80)
        self.desc_input.setStyleSheet(fs)
        lay.addWidget(self.desc_input)

        lay.addWidget(_lbl("IMPORTANCE  (1–100)"))
        score_row = QHBoxLayout()
        self.score_slider = QSlider(Qt.Horizontal)
        self.score_slider.setRange(1, 100)
        self.score_slider.setValue(50)
        self.score_slider.setStyleSheet("""
            QSlider::groove:horizontal { background: #1A1A1A; height: 6px; border-radius: 3px; }
            QSlider::handle:horizontal { background: #2ecc71; width: 14px; height: 14px;
                margin: -4px 0; border-radius: 7px; }
            QSlider::sub-page:horizontal { background: #2ecc71; border-radius: 3px; }
        """)
        self.score_val = QLabel("50")
        self.score_val.setFixedWidth(28)
        self.score_val.setStyleSheet(
            "color: #2ecc71; font-size: 12px; font-weight: 700; background: transparent; border: none;"
        )
        self.score_slider.valueChanged.connect(lambda v: self.score_val.setText(str(v)))
        score_row.addWidget(self.score_slider)
        score_row.addWidget(self.score_val)
        lay.addLayout(score_row)
        lay.addStretch()

        scroll.setWidget(fw)
        main.addWidget(scroll)

    def open_create(self, parent_id=None, parent_name=None):
        self._edit_id   = None
        self._parent_id = parent_id
        self._title.setText("New Node")
        self.name_input.clear()
        self.desc_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.score_slider.setValue(50)
        self._status.setText("")
        self._save_btn.setEnabled(True)
        if parent_id and parent_name:
            self._parent_lbl.setText(f"└─ Child of: {parent_name}")
            self._parent_lbl.setVisible(True)
        else:
            self._parent_lbl.setVisible(False)

    def open_edit(self, data: dict):
        self._edit_id   = data["id"]
        self._parent_id = data.get("parent_id")
        self._title.setText("Edit Node")
        self.name_input.setText(data["name"])
        self.desc_input.setPlainText(data["description"])
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == data["node_type"]:
                self.type_combo.setCurrentIndex(i)
                break
        self.score_slider.setValue(data["importance_score"])
        self._status.setText("")
        self._save_btn.setEnabled(True)
        self._parent_lbl.setVisible(False)

    def _cancel(self):
        self.hide()
        self.cancelled.emit()

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            self._status.setText("⚠  Name required!")
            return
        payload = {
            "universe_id":      self._universe_id,
            "name":             name,
            "node_type":        self.type_combo.currentData(),
            "description":      self.desc_input.toPlainText().strip() or None,
            "importance_score": self.score_slider.value(),
            "parent_id":        self._parent_id,
        }
        self._save_btn.setEnabled(False)
        self._status.setText("Saving...")
        self._status.setStyleSheet(
            "color: #2ecc71; font-size: 10px; background: transparent; border: none;"
        )
        self._worker = SaveNodeWorker(payload, self._edit_id)
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
# Universe Tree Panel (full cosmic hierarchy browser)
# ─────────────────────────────────────────────────────────
class UniverseTreePanel(QWidget):
    """Full-screen panel showing the cosmic hierarchy tree for one universe."""
    back_clicked = Signal()  # user clicked ← back to card grid

    def __init__(self, parent=None):
        super().__init__(parent)
        self._universe_data = {}
        self._nodes         = []   # flat list of all nodes
        self._load_worker   = None
        self._del_worker    = None

        self.setStyleSheet("background: #0D0D0D;")
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left: tree area ──
        left = QWidget()
        left.setStyleSheet("background: #0D0D0D;")
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)

        # Top bar
        top_bar = QFrame()
        top_bar.setFixedHeight(64)
        top_bar.setStyleSheet("background: #0D0D0D; border-bottom: 1px solid #1A1A1A;")
        bar_lay = QHBoxLayout(top_bar)
        bar_lay.setContentsMargins(24, 0, 24, 0)
        bar_lay.setSpacing(12)

        back_btn = QPushButton("←  Universes")
        back_btn.setFixedHeight(32)
        back_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #444;
                border: 1px solid #222; border-radius: 6px;
                font-size: 12px; font-weight: 600; padding: 0 14px;
            }
            QPushButton:hover { color: #AAA; border-color: #444; }
        """)
        back_btn.clicked.connect(self.back_clicked.emit)

        self._uni_label = QLabel("🌐  Universe")
        self._uni_label.setStyleSheet(
            "color: #00ADB5; font-size: 18px; font-weight: 900; "
            "letter-spacing: 2px; background: transparent; border: none;"
        )

        self._tree_status = QLabel("")
        self._tree_status.setStyleSheet(
            "color: #333; font-size: 11px; background: transparent; border: none;"
        )

        add_root_btn = QPushButton("+  Add Root Node")
        add_root_btn.setFixedHeight(32)
        add_root_btn.setStyleSheet("""
            QPushButton {
                background: #2ecc71; color: #000;
                border: none; border-radius: 6px;
                font-size: 12px; font-weight: 700; padding: 0 16px;
            }
            QPushButton:hover { background: #3de382; }
        """)
        add_root_btn.clicked.connect(self._add_root_node)

        bar_lay.addWidget(back_btn)
        bar_lay.addSpacing(8)
        bar_lay.addWidget(self._uni_label)
        bar_lay.addStretch()
        bar_lay.addWidget(self._tree_status)
        bar_lay.addWidget(add_root_btn)
        left_lay.addWidget(top_bar)

        # Tree widget
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setStyleSheet("""
            QTreeWidget {
                background: #0D0D0D;
                border: none;
                color: #CCCCCC;
                font-size: 13px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
            }
            QTreeWidget::item:hover {
                background: #111;
            }
            QTreeWidget::item:selected {
                background: #1A3A2A;
                color: #2ecc71;
            }
            QTreeWidget::branch {
                background: #0D0D0D;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                border-image: none;
                image: none;
            }
            QScrollBar:vertical { background: #111; width: 6px; }
            QScrollBar::handle:vertical { background: #2A2A2A; border-radius: 3px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #2ecc71; }
        """)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        left_lay.addWidget(self._tree)
        root.addWidget(left, 1)

        # ── Right: Node form panel ──
        self._form_panel = NodeFormPanel(universe_id=-1)
        self._form_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._form_panel.saved.connect(self._reload)
        self._form_panel.hide()
        root.addWidget(self._form_panel, 0)

    # ── Public API ─────────────────────────────────────────

    def load_universe(self, universe_data: dict):
        """Call this before showing the panel."""
        self._universe_data = universe_data
        self._form_panel._universe_id = universe_data["id"]
        self._uni_label.setText(f"🌐  {universe_data['name']}  ›  Cosmic Tree")
        self._reload()

    # ── Tree building ──────────────────────────────────────

    def _reload(self):
        self._tree_status.setText("Loading...")
        uid = self._universe_data.get("id")
        if not uid:
            return
        self._load_worker = LoadTreeWorker(uid)
        self._load_worker.done.connect(self._on_loaded)
        self._load_worker.error.connect(lambda e: self._tree_status.setText(f"Error: {e}"))
        self._load_worker.start()

    def _on_loaded(self, nodes: list):
        self._nodes = nodes
        self._tree.clear()

        # Build id → QTreeWidgetItem map
        items = {}
        for n in nodes:
            icon  = NODE_ICONS.get(n["node_type"], "📦")
            score = n["importance_score"]
            label = f"{icon}  {n['name']}"
            if n.get("description"):
                label += f"  —  {n['description'][:40]}"
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.UserRole, n)  # store full data
            item.setForeground(0, __import__('PySide6.QtGui', fromlist=['QColor']).QColor(
                "#CCCCCC" if n["parent_id"] else "#EEEEEE"
            ))
            # Make root nodes slightly bold
            if not n["parent_id"]:
                f = item.font(0)
                f.setWeight(700)
                item.setFont(0, f)
            items[n["id"]] = item

        # Insert into tree (parent first, then children)
        for n in nodes:
            item = items[n["id"]]
            if n["parent_id"] and n["parent_id"] in items:
                items[n["parent_id"]].addChild(item)
            else:
                self._tree.addTopLevelItem(item)

        self._tree.expandAll()
        count = len(nodes)
        self._tree_status.setText(f"{count} node{'s' if count != 1 else ''}")

    # ── Context menu & actions ─────────────────────────────

    def _show_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #111; color: #CCC;
                border: 1px solid #222; border-radius: 6px;
                padding: 4px;
            }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #1A3A2A; color: #2ecc71; }
        """)

        if item:
            node_data = item.data(0, Qt.UserRole)
            act_add_child = menu.addAction("+  Add Child Node")
            act_edit      = menu.addAction("✎  Edit")
            menu.addSeparator()
            act_del       = menu.addAction("✕  Delete (+ children)")

            action = menu.exec(self._tree.viewport().mapToGlobal(pos))
            if action == act_add_child:
                self._add_child_node(node_data)
            elif action == act_edit:
                self._edit_node(node_data)
            elif action == act_del:
                self._confirm_delete(node_data)
        else:
            act_root = menu.addAction("+  Add Root Node")
            action = menu.exec(self._tree.viewport().mapToGlobal(pos))
            if action == act_root:
                self._add_root_node()

    def _on_item_double_clicked(self, item, _col):
        node_data = item.data(0, Qt.UserRole)
        self._edit_node(node_data)

    def _add_root_node(self):
        self._form_panel.open_create(parent_id=None)
        self._form_panel.show()

    def _add_child_node(self, parent_data: dict):
        self._form_panel.open_create(
            parent_id=parent_data["id"],
            parent_name=parent_data["name"]
        )
        self._form_panel.show()

    def _edit_node(self, node_data: dict):
        self._form_panel.open_edit(node_data)
        self._form_panel.show()

    def _confirm_delete(self, node_data: dict):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete Node")
        child_warn = "<br><small style='color:#888'>Tamam children bhi delete ho jayenge.</small>"
        dlg.setText(
            f"<b style='color:#e74c3c'>'{node_data['name']}'</b> delete karna chahte ho?{child_warn}"
        )
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        dlg.setDefaultButton(QMessageBox.Cancel)
        dlg.setStyleSheet("""
            QMessageBox { background: #111; color: #CCC; }
            QPushButton { background: #1A1A1A; color: #CCC;
                border: 1px solid #333; border-radius: 5px; padding: 5px 18px; }
            QPushButton:hover { background: #222; }
        """)
        if dlg.exec() == QMessageBox.Yes:
            self._del_worker = DeleteNodeWorker(node_data["id"])
            self._del_worker.done.connect(lambda _: self._reload())
            self._del_worker.error.connect(
                lambda e: self._tree_status.setText(f"Error: {e}")
            )
            self._del_worker.start()



# ─────────────────────────────────────────────────────────
# Main Universes View
# ─────────────────────────────────────────────────────────
class UniversesViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._load_worker   = None
        self._delete_worker = None
        self._universes     = []
        self._setup_ui()
        self._load()

    # ── Build UI ──────────────────────────────────────────

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── QStackedWidget: page 0 = card grid, page 1 = tree ──
        self._stack = QStackedWidget()
        outer.addWidget(self._stack)

        # ─── Page 0: card grid ───────────────────────────
        card_page = QWidget()
        card_page.setStyleSheet("background: #0D0D0D;")
        card_lay = QVBoxLayout(card_page)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        # card page is itself a horizontal split (main area + form panel)
        card_split = QWidget()
        card_split.setStyleSheet("background: #0D0D0D;")
        card_split_lay = QHBoxLayout(card_split)
        card_split_lay.setContentsMargins(0, 0, 0, 0)
        card_split_lay.setSpacing(0)

        # ── Left: main area ──
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

        title = QLabel("🌐  Universes")
        title.setStyleSheet(
            "color: #00ADB5; font-size: 20px; font-weight: 900; "
            "letter-spacing: 2px; background: transparent; border: none;"
        )
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(
            "color: #333; font-size: 11px; background: transparent; border: none;"
        )

        self._new_btn = QPushButton("＋  New Universe")
        self._new_btn.setFixedHeight(34)
        self._new_btn.setStyleSheet("""
            QPushButton {
                background: #00ADB5; color: #000;
                border: none; border-radius: 7px;
                padding: 0 18px; font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background: #00C9D4; }
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
        self._search_input.setPlaceholderText("🔍  Search universes...")
        self._search_input.setFixedHeight(30)
        self._search_input.setFixedWidth(220)
        self._search_input.setStyleSheet("""
            QLineEdit {
                background: #111; color: #CCC;
                border: 1px solid #222; border-radius: 6px;
                padding: 0 12px; font-size: 12px;
            }
            QLineEdit:focus { border-color: #00ADB5; }
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
                selection-background-color: #00ADB5;
            }
        """
        self._canon_combo = QComboBox()
        self._canon_combo.addItem("All Canon Status", None)
        for opt in CANON_OPTIONS:
            self._canon_combo.addItem(opt.replace("_", " ").title(), opt)
        self._canon_combo.setStyleSheet(combo_style)
        self._canon_combo.currentIndexChanged.connect(self._load)

        f_lay.addWidget(self._search_input)
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
            QScrollBar::handle:vertical:hover { background: #00ADB5; }
        """)

        self._cards_widget = QWidget()
        self._cards_widget.setStyleSheet("background: #0D0D0D;")
        self._cards_layout = QGridLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(32, 24, 32, 32)
        self._cards_layout.setSpacing(16)
        self._cards_layout.setAlignment(Qt.AlignTop)

        self._scroll.setWidget(self._cards_widget)
        left_lay.addWidget(self._scroll)

        card_split_lay.addWidget(main_area)

        # ── Right: Slide-in form panel ──
        self._form_panel = UniverseFormPanel()
        self._form_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._form_panel.saved.connect(self._load)
        self._form_panel.hide()
        card_split_lay.addWidget(self._form_panel, 0)

        card_lay.addWidget(card_split)
        self._stack.addWidget(card_page)   # index 0

        # ─── Page 1: cosmic tree ─────────────────────────
        self._tree_panel = UniverseTreePanel()
        self._tree_panel.back_clicked.connect(self._show_cards)
        self._stack.addWidget(self._tree_panel)   # index 1

    # ── Navigation ────────────────────────────────────────

    def _show_cards(self):
        self._stack.setCurrentIndex(0)
        self._load()

    def _open_tree_for(self, data: dict):
        self._tree_panel.load_universe(data)
        self._stack.setCurrentIndex(1)

    def showEvent(self, event):
        super().showEvent(event)
        if self._stack.currentIndex() == 0:
            self._load()

    # ── Panel open/close ──────────────────────────────────

    def _open_create(self):
        self._form_panel.open_create()
        self._form_panel.show()

    def _open_edit(self, data: dict):
        self._form_panel.open_edit(data)
        self._form_panel.show()

    # ── Load data ─────────────────────────────────────────

    def _load(self):
        self._status_lbl.setText("Loading...")
        self._new_btn.setEnabled(False)
        canon_filter = self._canon_combo.currentData()
        name_filter  = self._search_input.text().strip()
        self._load_worker = LoadUniversesWorker(canon_filter, name_filter)
        self._load_worker.done.connect(self._on_loaded)
        self._load_worker.error.connect(self._on_error)
        self._load_worker.start()

    def _on_search_changed(self, text: str):
        if len(text) == 0 or len(text) >= 2:
            self._load()

    def _on_loaded(self, payload: list):
        universes, root_entities = payload
        self._universes = universes

        # Update Root Entities dropdown in form panel
        self._form_panel.root_combo.clear()
        self._form_panel.root_combo.addItem("None", None)
        for re in root_entities:
            self._form_panel.root_combo.addItem(re["name"], re["id"])

        self._rebuild_cards()
        count = len(universes)
        self._status_lbl.setText(f"{count} universe{'s' if count != 1 else ''}")
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

        if not self._universes:
            empty = QLabel("Koi universe nahi mila.\n\nUpar '＋ New Universe' click karein.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color: #222; font-size: 16px; padding: 60px; "
                "background: transparent; border: none;"
            )
            self._cards_layout.addWidget(empty, 0, 0, 1, 3)
            return

        cols = 3
        for i, data in enumerate(self._universes):
            card = UniverseCard(data)
            card.edit_clicked.connect(self._open_edit)
            card.delete_clicked.connect(self._confirm_delete)
            card.tree_clicked.connect(self._open_tree_for)   # ← wire tree button
            self._cards_layout.addWidget(card, i // cols, i % cols)

        remainder = len(self._universes) % cols
        if remainder:
            for j in range(cols - remainder):
                spacer = QWidget()
                spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                row = len(self._universes) // cols
                self._cards_layout.addWidget(spacer, row, remainder + j)

    # ── Delete ────────────────────────────────────────────

    def _confirm_delete(self, data: dict):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete Universe")
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
            self._delete_worker = DeleteUniverseWorker(data["id"])
            self._delete_worker.done.connect(lambda _: self._load())
            self._delete_worker.error.connect(self._on_error)
            self._delete_worker.start()


