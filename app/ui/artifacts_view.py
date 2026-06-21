"""
app/ui/artifacts_view.py
Zen AI — Artifacts CRUD Page (Phase 9F)
Theme: Cyan/Diamond  #00BCD4
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

ACCENT = "#00BCD4"
CANON_COLORS = {
    "canon":        ACCENT,
    "non_canon":    "#e74c3c",
    "alt_timeline": "#9b59b6",
    "experimental": "#f39c12",
}
CANON_OPTIONS = ["canon", "non_canon", "alt_timeline", "experimental"]


# ─── Workers ────────────────────────────────────────────
class LoadArtifactsWorker(QThread):
    done  = Signal(list)
    error = Signal(str)

    def __init__(self, universe_id=None, name_filter=None):
        super().__init__()
        self.universe_id = universe_id
        self.name_filter = name_filter

    def run(self):
        try:
            session = get_session()
            arts = crud.list_artifacts(
                session,
                universe_id=self.universe_id,
                name_contains=self.name_filter or None,
            )
            result = [
                {
                    "id":               a.id,
                    "name":             a.name,
                    "description":      a.description or "",
                    "powers_json":      a.powers_json or [],
                    "importance_score": a.importance_score,
                    "universe_id":      a.universe_id,
                    "universe_name":    a.universe.name if a.universe else "—",
                }
                for a in arts
            ]
            session.close()
            self.done.emit(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class LoadUniversesForArtWorker(QThread):
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


class SaveArtifactWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, data: dict, artifact_id: int = None):
        super().__init__()
        self.data        = data
        self.artifact_id = artifact_id

    def run(self):
        try:
            session = get_session()
            if self.artifact_id:
                crud.update_artifact(session, self.artifact_id, **self.data)
            else:
                crud.create_artifact(session, **self.data)
            session.close()
            self.done.emit("ok")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class DeleteArtifactWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, artifact_id: int):
        super().__init__()
        self.artifact_id = artifact_id

    def run(self):
        try:
            session = get_session()
            crud.delete_artifact(session, self.artifact_id)
            session.close()
            self.done.emit("ok")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


# ─── Artifact Card ──────────────────────────────────────
class ArtifactCard(QFrame):
    edit_clicked   = Signal(dict)
    delete_clicked = Signal(dict)

    def __init__(self, data: dict):
        super().__init__()
        self.data = data
        color = ACCENT

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
        name_lbl = QLabel(f"💎  {data['name']}")
        name_lbl.setStyleSheet(
            "color: #EEEEEE; font-size: 15px; font-weight: 700; background: transparent; border: none;"
        )
        uni_lbl = QLabel(f"🌐 {data['universe_name']}")
        uni_lbl.setStyleSheet(f"color: {color}44; font-size: 10px; background: transparent; border: none;")
        hdr.addWidget(name_lbl)
        hdr.addStretch()
        hdr.addWidget(uni_lbl)
        lay.addLayout(hdr)

        # Powers pills (top 3)
        powers = data.get("powers_json") or []
        if powers:
            pill_row = QHBoxLayout()
            pill_row.setSpacing(6)
            for p in powers[:3]:
                pill_lbl = QLabel(str(p))
                pill_lbl.setStyleSheet(
                    f"color: {color}; font-size: 9px; font-weight: 600; "
                    f"background: {color}12; border: 1px solid {color}33; "
                    "border-radius: 3px; padding: 1px 7px;"
                )
                pill_row.addWidget(pill_lbl)
            pill_row.addStretch()
            lay.addLayout(pill_row)

        # Description snippet
        desc = data.get("description", "")
        if desc:
            snippet = (desc[:85] + "…") if len(desc) > 85 else desc
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
        del_btn.setStyleSheet(self._btn("#e74c3c"))
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.data))
        foot.addWidget(score_lbl)
        foot.addStretch()
        foot.addWidget(edit_btn)
        foot.addSpacing(6)
        foot.addWidget(del_btn)
        lay.addLayout(foot)

    @staticmethod
    def _btn(color):
        return f"""
            QPushButton {{ background: transparent; color: {color}; border: 1px solid {color}44; border-radius: 5px; font-size: 11px; font-weight: 600; }}
            QPushButton:hover {{ background: {color}18; border-color: {color}; }}
        """


# ─── Form Panel ─────────────────────────────────────────
class ArtifactFormPanel(QFrame):
    saved     = Signal()
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._edit_id   = None
        self._worker    = None
        self._universes = []

        self.setFixedWidth(390)
        self.setStyleSheet("QFrame { background: #111111; border-left: 1px solid #1E1E1E; }")

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Fixed Header
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("background: #111111; border-bottom: 1px solid #1E1E1E;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 12, 0)
        h_lay.setSpacing(8)

        self._title = QLabel("New Artifact")
        self._title.setStyleSheet(f"color: {ACCENT}; font-size: 15px; font-weight: 800; background: transparent; border: none;")

        self._status = QLabel("")
        self._status.setStyleSheet("color: #e74c3c; font-size: 10px; background: transparent; border: none;")

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedSize(64, 30)
        self._cancel_btn.setStyleSheet("QPushButton { background: transparent; color: #666; border: 1px solid #333; border-radius: 5px; font-size: 12px; font-weight: 600; } QPushButton:hover { color: #AAA; border-color: #555; }")
        self._cancel_btn.clicked.connect(self._cancel)

        self._save_btn = QPushButton("✓  Save")
        self._save_btn.setFixedSize(80, 30)
        self._save_btn.setStyleSheet(f"QPushButton {{ background: {ACCENT}; color: #000; border: none; border-radius: 5px; font-size: 12px; font-weight: 700; }} QPushButton:hover {{ background: #00D4EE; }} QPushButton:disabled {{ background: #0A2A30; color: #555; }}")
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

        # Scrollable Fields
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

        lay.addWidget(_lbl("UNIVERSE  *"))
        self.universe_combo = QComboBox()
        self.universe_combo.setStyleSheet(fs)
        lay.addWidget(self.universe_combo)

        lay.addWidget(_lbl("ARTIFACT NAME  *"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g.  The Void Blade")
        self.name_input.setStyleSheet(fs)
        lay.addWidget(self.name_input)

        lay.addWidget(_lbl("DESCRIPTION"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Artifact ki powers, origin, history...")
        self.desc_input.setFixedHeight(90)
        self.desc_input.setStyleSheet(fs)
        lay.addWidget(self.desc_input)

        lay.addWidget(_lbl("POWERS  (comma separated)"))
        self.powers_input = QLineEdit()
        self.powers_input.setPlaceholderText("e.g.  Time Control, Invisibility, Telepathy")
        self.powers_input.setStyleSheet(fs)
        lay.addWidget(self.powers_input)

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
        lay.addStretch()

        scroll.setWidget(fw)
        main.addWidget(scroll)

    def set_universes(self, universes: list):
        self._universes = universes
        self.universe_combo.clear()
        for u in universes:
            self.universe_combo.addItem(u["name"], u["id"])

    def open_create(self):
        self._edit_id = None
        self._title.setText("New Artifact")
        self._status.setText("")
        self._save_btn.setEnabled(True)
        self.name_input.clear()
        self.desc_input.clear()
        self.powers_input.clear()
        self.score_slider.setValue(50)
        if self.universe_combo.count():
            self.universe_combo.setCurrentIndex(0)

    def open_edit(self, data: dict):
        self._edit_id = data["id"]
        self._title.setText("Edit Artifact")
        self._status.setText("")
        self._save_btn.setEnabled(True)
        for i in range(self.universe_combo.count()):
            if self.universe_combo.itemData(i) == data["universe_id"]:
                self.universe_combo.setCurrentIndex(i)
                break
        self.name_input.setText(data["name"])
        self.desc_input.setPlainText(data["description"])
        powers = data.get("powers_json") or []
        self.powers_input.setText(", ".join(str(p) for p in powers))
        self.score_slider.setValue(data["importance_score"])

    def _cancel(self):
        self.hide()
        self.cancelled.emit()

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            self._status.setText("⚠  Name required!")
            return
        uid = self.universe_combo.currentData()
        if uid is None:
            self._status.setText("⚠  Universe select karein!")
            return

        raw_powers = self.powers_input.text().strip()
        powers_list = [p.strip() for p in raw_powers.split(",") if p.strip()] if raw_powers else []

        payload = {
            "universe_id":      uid,
            "name":             name,
            "description":      self.desc_input.toPlainText().strip() or None,
            "powers_json":      powers_list,
            "importance_score": self.score_slider.value(),
        }
        self._save_btn.setEnabled(False)
        self._status.setText("Saving...")
        self._status.setStyleSheet(f"color: {ACCENT}; font-size: 10px; background: transparent; border: none;")
        self._worker = SaveArtifactWorker(payload, self._edit_id)
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
class ArtifactsViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._load_worker   = None
        self._uni_worker    = None
        self._delete_worker = None
        self._artifacts     = []
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

        title = QLabel("💎  Artifacts")
        title.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: 900; letter-spacing: 2px; background: transparent; border: none;")
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #333; font-size: 11px; background: transparent; border: none;")
        self._new_btn = QPushButton("＋  New Artifact")
        self._new_btn.setFixedHeight(34)
        self._new_btn.setStyleSheet(f"QPushButton {{ background: {ACCENT}; color: #000; border: none; border-radius: 7px; padding: 0 18px; font-size: 13px; font-weight: 700; }} QPushButton:hover {{ background: #00D4EE; }}")
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
        self._search_input.setPlaceholderText("🔍  Search artifacts...")
        self._search_input.setFixedHeight(30)
        self._search_input.setFixedWidth(220)
        self._search_input.setStyleSheet(f"QLineEdit {{ background: #111; color: #CCC; border: 1px solid #222; border-radius: 6px; padding: 0 12px; font-size: 12px; }} QLineEdit:focus {{ border-color: {ACCENT}; }}")
        self._search_input.textChanged.connect(self._on_search_changed)

        combo_style = f"QComboBox {{ background: #111; color: #888; border: 1px solid #222; border-radius: 6px; padding: 0 10px; font-size: 12px; min-width: 140px; height: 30px; }} QComboBox QAbstractItemView {{ background: #111; color: #CCC; selection-background-color: {ACCENT}; }}"
        self._uni_combo = QComboBox()
        self._uni_combo.addItem("All Universes", None)
        self._uni_combo.setStyleSheet(combo_style)
        self._uni_combo.currentIndexChanged.connect(self._load_artifacts)

        f_lay.addWidget(self._search_input)
        f_lay.addWidget(self._uni_combo)
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

        self._form_panel = ArtifactFormPanel()
        self._form_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._form_panel.saved.connect(self._load_artifacts)
        self._form_panel.hide()
        root.addWidget(self._form_panel, 0)


    def _load_universes(self):
        self._uni_worker = LoadUniversesForArtWorker()
        self._uni_worker.done.connect(self._on_universes_loaded)
        self._uni_worker.error.connect(lambda _: self._load_artifacts())
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
        self._load_artifacts()

    def _open_create(self):
        self._form_panel.set_universes(self._universes)
        self._form_panel.open_create()
        self._form_panel.show()

    def _open_edit(self, data: dict):
        self._form_panel.set_universes(self._universes)
        self._form_panel.open_edit(data)
        self._form_panel.show()

    def _load_artifacts(self):
        self._status_lbl.setText("Loading...")
        self._new_btn.setEnabled(False)
        uid         = self._uni_combo.currentData()
        name_filter = self._search_input.text().strip()
        self._load_worker = LoadArtifactsWorker(uid, name_filter)
        self._load_worker.done.connect(self._on_loaded)
        self._load_worker.error.connect(self._on_error)
        self._load_worker.start()

    def _on_search_changed(self, text: str):
        if len(text) == 0 or len(text) >= 2:
            self._load_artifacts()

    def _on_loaded(self, artifacts: list):
        self._artifacts = artifacts
        self._rebuild_cards()
        count = len(artifacts)
        self._status_lbl.setText(f"{count} artifact{'s' if count != 1 else ''}")
        self._new_btn.setEnabled(True)

    def _on_error(self, msg: str):
        self._status_lbl.setText(f"Error: {msg}")
        self._new_btn.setEnabled(True)

    def _rebuild_cards(self):
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._artifacts:
            empty = QLabel("Koi artifact nahi mila.\n\nUpar '＋ New Artifact' click karein.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #222; font-size: 16px; padding: 60px; background: transparent; border: none;")
            self._cards_layout.addWidget(empty, 0, 0, 1, 3)
            return

        cols = 3
        for i, data in enumerate(self._artifacts):
            card = ArtifactCard(data)
            card.edit_clicked.connect(self._open_edit)
            card.delete_clicked.connect(self._confirm_delete)
            self._cards_layout.addWidget(card, i // cols, i % cols)

        remainder = len(self._artifacts) % cols
        if remainder:
            for j in range(cols - remainder):
                spacer = QWidget()
                spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._cards_layout.addWidget(spacer, len(self._artifacts) // cols, remainder + j)

    def _confirm_delete(self, data: dict):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete Artifact")
        dlg.setText(f"<b style='color:#e74c3c'>'{data['name']}'</b> delete karna chahte ho?<br><small style='color:#666'>Yeh action undo nahi hogi.</small>")
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        dlg.setDefaultButton(QMessageBox.Cancel)
        dlg.setStyleSheet("QMessageBox { background: #111; color: #CCC; font-size: 13px; } QPushButton { background: #1A1A1A; color: #CCC; border: 1px solid #333; border-radius: 6px; padding: 6px 20px; } QPushButton:hover { background: #222; }")
        if dlg.exec() == QMessageBox.Yes:
            self._delete_worker = DeleteArtifactWorker(data["id"])
            self._delete_worker.done.connect(lambda _: self._load_artifacts())
            self._delete_worker.error.connect(self._on_error)
            self._delete_worker.start()
