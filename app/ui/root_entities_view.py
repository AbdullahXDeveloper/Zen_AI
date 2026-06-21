"""
app/ui/root_entities_view.py
Zen AI — Root Entities CRUD Page
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QLineEdit, QComboBox,
    QTextEdit, QSlider, QDialog, QDialogButtonBox,
    QGridLayout, QSizePolicy, QMessageBox, QSpacerItem
)
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont, QIntValidator

from app.database.db_init import get_session
from app.database import crud
from app.utils.dashboard_generator import generate_entity_dashboard


# ─────────────────────────────────────────────────────────
# Workers
# ─────────────────────────────────────────────────────────
class LoadRootEntitiesWorker(QThread):
    done  = Signal(list)
    error = Signal(str)

    def __init__(self, type_filter=None):
        super().__init__()
        self.type_filter = type_filter

    def run(self):
        try:
            session = get_session()
            entities = crud.list_root_entities(
                session,
                type=self.type_filter or None
            )
            result = [
                {
                    "id":          e.id,
                    "name":        e.name,
                    "type":        e.type or "",
                    "description": e.description or "",
                    "notes":       e.notes or "",
                    "importance_score": e.importance_score,
                }
                for e in entities
            ]
            session.close()
            self.done.emit(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class SaveRootEntityWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, data: dict, entity_id: int = None):
        super().__init__()
        self.data        = data
        self.entity_id   = entity_id

    def run(self):
        try:
            session = get_session()
            if self.entity_id:
                crud.update_root_entity(session, self.entity_id, **self.data)
            else:
                crud.create_root_entity(session, **self.data)
            session.close()
            generate_entity_dashboard()
            self.done.emit("ok")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class DeleteRootEntityWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id

    def run(self):
        try:
            session = get_session()
            success = crud.delete_root_entity(session, self.entity_id)
            session.close()
            if success:
                generate_entity_dashboard()
                self.done.emit("ok")
            else:
                self.error.emit("Entity not found or could not be deleted.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


# ─────────────────────────────────────────────────────────
# Root Entity Card
# ─────────────────────────────────────────────────────────
class RootEntityCard(QFrame):
    edit_clicked   = Signal(dict)
    delete_clicked = Signal(dict)

    def __init__(self, data: dict):
        super().__init__()
        self.data  = data
        color = "#FFD700"  # Golden color for Root Entities

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
        lay.setSpacing(6)

        # ── Header row ──
        hdr = QHBoxLayout()

        name_lbl = QLabel(f"★  {data['name']}")
        name_lbl.setStyleSheet(
            "color: #EEEEEE; font-size: 15px; font-weight: 700; "
            "background: transparent; border: none;"
        )

        type_text = data['type'] if data['type'] else "Unknown Type"
        type_lbl = QLabel(type_text.upper())
        type_lbl.setStyleSheet(
            f"color: {color}; font-size: 9px; font-weight: 700; "
            f"background: {color}18; border: 1px solid {color}44; "
            "border-radius: 4px; padding: 2px 8px;"
        )

        hdr.addWidget(name_lbl)
        hdr.addStretch()
        hdr.addWidget(type_lbl)
        lay.addLayout(hdr)

        # ── Description ──
        desc = data["description"][:90] + "…" if len(data["description"]) > 90 else data["description"]
        desc_lbl = QLabel(desc or "No description.")
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(
            "color: #555; font-size: 12px; background: transparent; border: none;"
        )
        lay.addWidget(desc_lbl)
        
        # ── Notes snippet ──
        if data["notes"]:
            notes_snippet = data["notes"][:40] + "…" if len(data["notes"]) > 40 else data["notes"]
            notes_lbl = QLabel(f"<i>Notes: {notes_snippet}</i>")
            notes_lbl.setStyleSheet("color: #777; font-size: 10px; background: transparent; border: none;")
            lay.addWidget(notes_lbl)

        lay.addStretch()

        # ── Footer row ──
        foot = QHBoxLayout()
        score_lbl = QLabel(f"★ Importance: {data['importance_score']}")
        score_lbl.setStyleSheet(
            f"color: {color}88; font-size: 11px; background: transparent; border: none;"
        )

        edit_btn = QPushButton("✎  Edit")
        edit_btn.setFixedSize(70, 26)
        edit_btn.setStyleSheet(self._action_btn(color))
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
# Slide-in Form Panel
# ─────────────────────────────────────────────────────────
class RootEntityFormPanel(QFrame):
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

        self._title = QLabel("New Root Entity")
        self._title.setStyleSheet(
            "color: #FFD700; font-size: 15px; font-weight: 800; "
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
                background: #FFD700; color: #000;
                border: none; border-radius: 5px;
                font-size: 12px; font-weight: 700;
            }
            QPushButton:hover { background: #FFEA00; }
            QPushButton:disabled { background: #3A3A00; color: #555; }
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
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color: #FFD700; }
            QComboBox QAbstractItemView {
                background: #111; color: #CCC;
                selection-background-color: #FFD700;
                selection-color: #000;
            }
        """

        lay.addWidget(_lbl("NAME  *"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g.  OM_X")
        self.name_input.setStyleSheet(fs)
        lay.addWidget(self.name_input)
        
        lay.addWidget(_lbl("TYPE  (you can type a custom value)"))
        self.type_input = QComboBox()
        self.type_input.setEditable(True)
        self.type_input.addItems(["Root Entity", "Cosmic Structure", "Primordial Force", "Multiversal Anchor"])
        self.type_input.lineEdit().setPlaceholderText("Select or type custom...")
        self.type_input.setStyleSheet(fs)
        lay.addWidget(self.type_input)

        lay.addWidget(_lbl("DESCRIPTION"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Brief description of this entity...")
        self.desc_input.setFixedHeight(80)
        self.desc_input.setStyleSheet(fs)
        lay.addWidget(self.desc_input)
        
        lay.addWidget(_lbl("PRIVATE NOTES"))
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Hidden lore, true intentions, creator notes...")
        self.notes_input.setFixedHeight(80)
        self.notes_input.setStyleSheet(fs)
        lay.addWidget(self.notes_input)

        lay.addWidget(_lbl("IMPORTANCE SCORE  (1 – 100)"))
        score_row = QHBoxLayout()
        self.score_slider = QSlider(Qt.Horizontal)
        self.score_slider.setRange(1, 100)
        self.score_slider.setValue(100)
        self.score_slider.setStyleSheet("""
            QSlider::groove:horizontal { background: #1A1A1A; height: 6px; border-radius: 3px; }
            QSlider::handle:horizontal { background: #FFD700; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }
            QSlider::sub-page:horizontal { background: #FFD700; border-radius: 3px; }
        """)
        self.score_val = QLabel("100")
        self.score_val.setFixedWidth(30)
        self.score_val.setStyleSheet(
            "color: #FFD700; font-size: 13px; font-weight: 700; background: transparent; border: none;"
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
        self._title.setText("New Root Entity")
        self.name_input.clear()
        self.type_input.setCurrentText("Root Entity")
        self.desc_input.clear()
        self.notes_input.clear()
        self.score_slider.setValue(100)
        self._status.setText("")
        self._save_btn.setEnabled(True)

    def open_edit(self, data: dict):
        self._edit_id = data["id"]
        self._title.setText("Edit Root Entity")
        self.name_input.setText(data["name"])
        self.type_input.setCurrentText(data["type"])
        self.desc_input.setPlainText(data["description"])
        self.notes_input.setPlainText(data["notes"])
        self.score_slider.setValue(data["importance_score"])
        self._status.setText("")
        self._save_btn.setEnabled(True)

    # ── Internal ──────────────────────────────────────────

    def _cancel(self):
        """Close immediately."""
        self.hide()
        self.cancelled.emit()

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            self._status.setText("⚠  Name required!")
            return

        payload = {
            "name":             name,
            "type":             self.type_input.currentText().strip(),
            "description":      self.desc_input.toPlainText().strip(),
            "notes":            self.notes_input.toPlainText().strip(),
            "importance_score": self.score_slider.value(),
        }

        self._save_btn.setEnabled(False)
        self._status.setText("Saving...")
        self._status.setStyleSheet(
            "color: #FFD700; font-size: 11px; background: transparent; border: none;"
        )

        self._worker = SaveRootEntityWorker(payload, self._edit_id)
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
            "color: #e74c3c; font-size: 11px; background: transparent; border: none;"
        )
        self._save_btn.setEnabled(True)


# ─────────────────────────────────────────────────────────
# Main Root Entities View
# ─────────────────────────────────────────────────────────
class RootEntitiesViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._load_worker   = None
        self._delete_worker = None
        self._entities      = []
        
        # Protect seeded root entities
        self._protected_names = ["K", "_LA", "OM_X", "Zendrix Tree"]
        
        self._setup_ui()
        self._load()

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

        title = QLabel("★  Root Entities")
        title.setStyleSheet(
            "color: #FFD700; font-size: 20px; font-weight: 900; "
            "letter-spacing: 2px; background: transparent; border: none;"
        )
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(
            "color: #333; font-size: 11px; background: transparent; border: none;"
        )

        self._new_btn = QPushButton("＋  New Root Entity")
        self._new_btn.setFixedHeight(34)
        self._new_btn.setStyleSheet("""
            QPushButton {
                background: #FFD700; color: #000;
                border: none; border-radius: 7px;
                padding: 0 18px; font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background: #FFEA00; }
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

        combo_style = """
            QComboBox {
                background: #111; color: #888;
                border: 1px solid #222; border-radius: 6px;
                padding: 0 10px; font-size: 12px;
                min-width: 160px; height: 30px;
            }
            QComboBox:hover { border-color: #333; }
            QComboBox QAbstractItemView {
                background: #111; color: #CCC;
                selection-background-color: #FFD700;
                selection-color: #000;
            }
        """
        self._type_combo = QComboBox()
        self._type_combo.addItem("All Entity Types", None)
        self._type_combo.addItems(["Root Entity", "Cosmic Structure", "Primordial Force"])
        self._type_combo.setStyleSheet(combo_style)
        self._type_combo.currentIndexChanged.connect(self._load)

        f_lay.addWidget(self._type_combo)
        f_lay.addStretch()
        left_lay.addWidget(filter_bar)

        # ── Cards scroll area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: #0D0D0D; }
            QScrollBar:vertical { background: #111; width: 6px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: #2A2A2A; border-radius: 3px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #FFD700; }
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
        self._form_panel = RootEntityFormPanel()
        self._form_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._form_panel.saved.connect(self._load)
        self._form_panel.hide()
        root.addWidget(self._form_panel, 0)


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
        type_filter = self._type_combo.currentData()
        self._load_worker = LoadRootEntitiesWorker(type_filter)
        self._load_worker.done.connect(self._on_loaded)
        self._load_worker.error.connect(self._on_error)
        self._load_worker.start()

    def _on_loaded(self, entities: list):
        self._entities = entities
        self._rebuild_cards()
        count = len(entities)
        self._status_lbl.setText(f"{count} entit{'y' if count == 1 else 'ies'}")
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

        if not self._entities:
            empty = QLabel("No Root Entities found.\n\nClick '＋ New Root Entity' to add one.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color: #222; font-size: 16px; padding: 60px; "
                "background: transparent; border: none;"
            )
            self._cards_layout.addWidget(empty, 0, 0, 1, 3)
            return

        cols = 3
        for i, data in enumerate(self._entities):
            card = RootEntityCard(data)
            card.edit_clicked.connect(self._open_edit)
            card.delete_clicked.connect(self._confirm_delete)
            self._cards_layout.addWidget(card, i // cols, i % cols)

        remainder = len(self._entities) % cols
        if remainder:
            for j in range(cols - remainder):
                spacer = QWidget()
                spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                row = len(self._entities) // cols
                self._cards_layout.addWidget(spacer, row, remainder + j)

    # ── Delete ────────────────────────────────────────────

    def _confirm_delete(self, data: dict):
        if data['name'] in self._protected_names:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Protected Entity")
            dlg.setText(
                f"<b style='color:#FFD700'>'{data['name']}'</b> is a core seeded Root Entity.<br>"
                "Deleting it is heavily discouraged as it may break cosmic connections."
            )
            dlg.setInformativeText("Are you absolutely sure you want to proceed?")
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
            if dlg.exec() != QMessageBox.Yes:
                return
        else:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Delete Root Entity")
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
            if dlg.exec() != QMessageBox.Yes:
                return

        self._delete_worker = DeleteRootEntityWorker(data["id"])
        self._delete_worker.done.connect(lambda _: self._load())
        self._delete_worker.error.connect(self._on_error)
        self._delete_worker.start()
