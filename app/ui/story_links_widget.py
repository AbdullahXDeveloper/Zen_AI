"""
app/ui/story_links_widget.py
Zen AI — Reusable Story Links Widget

Embeds in any entity form panel to allow linking that entity
to any Story (across any universe), with a custom link name.

Usage:
    widget = StoryLinksWidget(entity_type="character")
    widget.load_links(entity_id=5)       # call after entity is saved
    widget.save_links(entity_id=5)       # call on form save (handles new links)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QComboBox, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal

from app.database.db_init import get_session
from app.database import crud

ACCENT = "#00ADB5"

MODE_ICONS = {
    "canon": "📖", "non_canon": "📝", "what_if": "🔮",
    "alt_timeline": "🌀", "rpg_sim": "🎲",
}


# ─────────────────────────────────────────────────────────
# Workers
# ─────────────────────────────────────────────────────────

class LoadLinksWorker(QThread):
    done  = Signal(list)
    error = Signal(str)

    def __init__(self, entity_type: str, entity_id: int):
        super().__init__()
        self.entity_type = entity_type
        self.entity_id   = entity_id

    def run(self):
        try:
            session = get_session()
            links = crud.list_story_links(session, self.entity_type, self.entity_id)
            all_stories = crud.list_all_stories_enriched(session)
            session.close()
            self.done.emit([links, all_stories])
        except Exception as e:
            import traceback; traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class SaveLinkWorker(QThread):
    done  = Signal(int)   # emits new link id
    error = Signal(str)

    def __init__(self, entity_type: str, entity_id: int,
                 story_id: int, link_name: str):
        super().__init__()
        self.entity_type = entity_type
        self.entity_id   = entity_id
        self.story_id    = story_id
        self.link_name   = link_name

    def run(self):
        try:
            session = get_session()
            lnk = crud.create_story_link(
                session,
                source_entity_type=self.entity_type,
                source_entity_id=self.entity_id,
                story_id=self.story_id,
                link_name=self.link_name or None,
            )
            session.close()
            self.done.emit(lnk.id)
        except Exception as e:
            import traceback; traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


class DeleteLinkWorker(QThread):
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, link_id: int):
        super().__init__()
        self.link_id = link_id

    def run(self):
        try:
            session = get_session()
            crud.delete_story_link(session, self.link_id)
            session.close()
            self.done.emit("ok")
        except Exception as e:
            import traceback; traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


# ─────────────────────────────────────────────────────────
# Link Row (a single linked story pill/row)
# ─────────────────────────────────────────────────────────

class LinkRow(QFrame):
    remove_clicked = Signal(int)   # link_id

    def __init__(self, link_data: dict):
        super().__init__()
        self.link_id = link_data["id"]
        mode_icon    = MODE_ICONS.get(link_data.get("story_mode", ""), "📖")

        self.setStyleSheet("""
            QFrame {
                background: #0D0D0D;
                border: 1px solid #1E1E1E;
                border-radius: 6px;
            }
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(44)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 8, 0)
        row.setSpacing(8)

        # Story title
        title_lbl = QLabel(f"{mode_icon} {link_data['story_title']}")
        title_lbl.setStyleSheet(
            "color: #CCCCCC; font-size: 12px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        title_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Universe badge
        uni_lbl = QLabel(link_data["universe_name"])
        uni_lbl.setStyleSheet(
            f"color: {ACCENT}88; font-size: 9px; font-weight: 600; "
            f"background: {ACCENT}12; border: 1px solid {ACCENT}33; "
            "border-radius: 3px; padding: 1px 6px;"
        )

        # Link name
        name = link_data.get("link_name", "")
        if name:
            name_lbl = QLabel(f'"{name}"')

            name_lbl.setStyleSheet(
                "color: #555; font-size: 10px; font-style: italic; "
                "background: transparent; border: none;"
            )
            row.addWidget(title_lbl)
            row.addWidget(uni_lbl)
            row.addWidget(name_lbl)
        else:
            row.addWidget(title_lbl)
            row.addWidget(uni_lbl)

        # Remove button
        rm_btn = QPushButton("✕")
        rm_btn.setFixedSize(20, 20)
        rm_btn.setToolTip("Remove link")
        rm_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #333;
                border: none; font-size: 11px; border-radius: 3px;
            }
            QPushButton:hover { color: #e74c3c; background: #1A1A1A; }
        """)
        rm_btn.clicked.connect(lambda: self.remove_clicked.emit(self.link_id))
        row.addWidget(rm_btn)


# ─────────────────────────────────────────────────────────
# Add Link Mini-Form (inline)
# ─────────────────────────────────────────────────────────

class AddLinkForm(QFrame):
    link_saved  = Signal(dict)  # emits link data dict ready to display
    cancelled   = Signal()

    def __init__(self, entity_type: str, entity_id: int,
                 all_stories: list, parent=None):
        super().__init__(parent)
        self._entity_type = entity_type
        self._entity_id   = entity_id
        self._all_stories = all_stories
        self._worker      = None

        self.setStyleSheet("""
            QFrame {
                background: #111;
                border: 1px solid #00ADB544;
                border-radius: 8px;
            }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        fs = f"""
            QLineEdit, QComboBox {{
                background: #0D0D0D; color: #CCC;
                border: 1px solid #222; border-radius: 5px;
                padding: 5px 10px; font-size: 12px;
            }}
            QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
            QComboBox QAbstractItemView {{
                background: #111; color: #CCC;
                selection-background-color: {ACCENT};
            }}
        """

        def _lbl(t):
            l = QLabel(t)
            l.setStyleSheet(
                "color: #444; font-size: 9px; font-weight: 700; "
                "letter-spacing: 1px; background: transparent; border: none;"
            )
            return l

        # Universe filter
        lay.addWidget(_lbl("FILTER BY UNIVERSE"))
        self._uni_combo = QComboBox()
        self._uni_combo.setStyleSheet(fs)
        self._uni_combo.addItem("All Universes", None)
        # Build unique universe list from stories
        seen = set()
        for s in all_stories:
            uid = s.get("universe_id")
            if uid not in seen:
                seen.add(uid)
                self._uni_combo.addItem(s["universe_name"], uid)
        self._uni_combo.currentIndexChanged.connect(self._filter_stories)
        lay.addWidget(self._uni_combo)

        # Story picker
        lay.addWidget(_lbl("SELECT STORY  *"))
        self._story_combo = QComboBox()
        self._story_combo.setStyleSheet(fs)
        self._populate_stories(None)
        lay.addWidget(self._story_combo)

        # Link name
        lay.addWidget(_lbl("LINK NAME  (optional)"))
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText('e.g. "Origin Story", "Referenced In"')
        self._name_input.setStyleSheet(fs)
        lay.addWidget(self._name_input)

        # Status
        self._status = QLabel("")
        self._status.setStyleSheet(
            "color: #e74c3c; font-size: 10px; background: transparent; border: none;"
        )
        lay.addWidget(self._status)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        save_btn = QPushButton("＋ Add Link")
        save_btn.setFixedHeight(28)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: #000;
                border: none; border-radius: 5px;
                font-size: 11px; font-weight: 700; padding: 0 14px;
            }}
            QPushButton:hover {{ background: #00C9D4; }}
            QPushButton:disabled {{ background: #1A3A3A; color: #555; }}
        """)
        save_btn.clicked.connect(self._save)
        self._save_btn = save_btn

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #555;
                border: 1px solid #222; border-radius: 5px;
                font-size: 11px; padding: 0 14px;
            }
            QPushButton:hover { color: #888; border-color: #444; }
        """)
        cancel_btn.clicked.connect(self.cancelled.emit)

        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

    def _populate_stories(self, universe_id):
        self._story_combo.clear()
        self._story_combo.addItem("— Select a story —", None)
        for s in self._all_stories:
            if universe_id is None or s.get("universe_id") == universe_id:
                icon = MODE_ICONS.get(s.get("story_mode", ""), "📖")
                self._story_combo.addItem(
                    f"{icon} {s['title']}  [{s['universe_name']}]", s["id"]
                )

    def _filter_stories(self):
        uid = self._uni_combo.currentData()
        self._populate_stories(uid)

    def _save(self):
        story_id = self._story_combo.currentData()
        if story_id is None:
            self._status.setText("⚠  Story select karein!")
            return

        link_name = self._name_input.text().strip()
        if self._entity_id is None:
            # Entity not saved yet — signal with pending data
            # Find story info
            story_data = next(
                (s for s in self._all_stories if s["id"] == story_id), {}
            )
            self.link_saved.emit({
                "id":           None,  # pending
                "story_id":     story_id,
                "story_title":  story_data.get("title", ""),
                "universe_name": story_data.get("universe_name", "—"),
                "link_name":    link_name,
                "story_mode":   story_data.get("story_mode", ""),
                "_pending": True,
            })
            return

        self._save_btn.setEnabled(False)
        self._status.setText("Saving...")
        self._status.setStyleSheet(
            f"color: {ACCENT}; font-size: 10px; background: transparent; border: none;"
        )
        self._worker = SaveLinkWorker(
            self._entity_type, self._entity_id, story_id, link_name
        )
        story_data = next(
            (s for s in self._all_stories if s["id"] == story_id), {}
        )
        self._pending_data = {
            "story_id":     story_id,
            "story_title":  story_data.get("title", ""),
            "universe_name": story_data.get("universe_name", "—"),
            "link_name":    link_name,
            "story_mode":   story_data.get("story_mode", ""),
        }
        self._worker.done.connect(self._on_saved)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_saved(self, link_id: int):
        self._save_btn.setEnabled(True)
        self._status.setText("")
        data = dict(self._pending_data)
        data["id"] = link_id
        self.link_saved.emit(data)

    def _on_error(self, msg: str):
        self._status.setText(f"⚠  {msg}")
        self._save_btn.setEnabled(True)


# ─────────────────────────────────────────────────────────
# Main StoryLinksWidget
# ─────────────────────────────────────────────────────────

class StoryLinksWidget(QWidget):
    """
    Reusable collapsible widget that shows and edits story links for any entity.

    Usage:
        self._links_widget = StoryLinksWidget("character")
        lay.addWidget(self._links_widget)

        # When opening an existing entity:
        self._links_widget.load_for_entity(entity_id)

        # When opening "new" entity form:
        self._links_widget.set_pending_entity(None)
    """

    def __init__(self, entity_type: str, parent=None):
        super().__init__(parent)
        self._entity_type  = entity_type
        self._entity_id    = None
        self._all_stories  = []
        self._links        = []         # list of link data dicts
        self._pending_links = []        # links queued before entity is saved
        self._workers      = []
        self._add_form     = None

        self.setStyleSheet("background: transparent;")
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(6)

        # ── Section header ──
        hdr_row = QHBoxLayout()
        hdr_lbl = QLabel("🔗  LINKED STORY ARTIFACTS")
        hdr_lbl.setStyleSheet(
            "color: #333; font-size: 10px; font-weight: 700; "
            "letter-spacing: 1px; background: transparent; border: none;"
        )
        self._add_btn = QPushButton("＋ Add Link")
        self._add_btn.setFixedHeight(22)
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {ACCENT};
                border: 1px solid {ACCENT}44; border-radius: 4px;
                font-size: 10px; font-weight: 600; padding: 0 10px;
            }}
            QPushButton:hover {{ background: {ACCENT}18; border-color: {ACCENT}; }}
        """)
        self._add_btn.clicked.connect(self._show_add_form)
        hdr_row.addWidget(hdr_lbl)
        hdr_row.addStretch()
        hdr_row.addWidget(self._add_btn)
        main.addLayout(hdr_row)

        # Separator line
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #1A1A1A; border: none;")
        main.addWidget(sep)

        # ── Links container ──
        self._links_container = QVBoxLayout()
        self._links_container.setSpacing(4)
        self._links_container.setContentsMargins(0, 0, 0, 0)
        main.addLayout(self._links_container)

        # ── Empty state label ──
        self._empty_lbl = QLabel("No story links yet.")
        self._empty_lbl.setStyleSheet(
            "color: #2A2A2A; font-size: 11px; padding: 4px 0; "
            "background: transparent; border: none;"
        )
        main.addWidget(self._empty_lbl)

        # ── Add form placeholder ──
        self._form_container = QVBoxLayout()
        self._form_container.setContentsMargins(0, 0, 0, 0)
        main.addLayout(self._form_container)

    # ── Public API ─────────────────────────────────────────

    def load_for_entity(self, entity_id: int):
        """Call this when opening an existing entity to load its story links."""
        self._entity_id = entity_id
        self._pending_links = []
        w = LoadLinksWorker(self._entity_type, entity_id)
        w.done.connect(self._on_loaded)
        w.error.connect(lambda _: None)
        w.start()
        self._workers.append(w)

    def set_pending_entity(self):
        """Call this for a NEW entity (not yet saved). Links will be pending."""
        self._entity_id = None
        self._pending_links = []
        self._clear_link_rows()
        self._update_empty_state()
        # Still load all stories so the picker works
        w = LoadLinksWorker(self._entity_type, -1)
        w.done.connect(self._on_stories_loaded)
        w.error.connect(lambda _: None)
        w.start()
        self._workers.append(w)

    def flush_pending_links(self, entity_id: int):
        """
        After a new entity is saved, call this with the real entity_id
        to persist any pending links that were added before the entity existed.
        """
        self._entity_id = entity_id
        for pd in self._pending_links:
            w = SaveLinkWorker(
                self._entity_type, entity_id,
                pd["story_id"], pd.get("link_name") or None
            )
            w.done.connect(lambda _: None)
            w.error.connect(lambda _: None)
            w.start()
            self._workers.append(w)
        self._pending_links = []

    # ── Internal ───────────────────────────────────────────

    def _on_loaded(self, payload: list):
        links, all_stories = payload
        self._all_stories = all_stories
        self._links = links
        self._clear_link_rows()
        for lnk in links:
            self._add_link_row(lnk)
        self._update_empty_state()

    def _on_stories_loaded(self, payload: list):
        """Only called for new-entity mode — just grab the story list."""
        _, all_stories = payload
        self._all_stories = all_stories

    def _clear_link_rows(self):
        while self._links_container.count():
            item = self._links_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_link_row(self, lnk: dict):
        row = LinkRow(lnk)
        row.remove_clicked.connect(self._on_remove)
        self._links_container.addWidget(row)

    def _update_empty_state(self):
        has_links = (self._links_container.count() > 0)
        self._empty_lbl.setVisible(not has_links)

    def _show_add_form(self):
        # Hide existing form if open
        self._hide_add_form()

        self._add_form = AddLinkForm(
            self._entity_type, self._entity_id, self._all_stories
        )
        self._add_form.link_saved.connect(self._on_link_added)
        self._add_form.cancelled.connect(self._hide_add_form)
        self._form_container.addWidget(self._add_form)
        self._add_btn.setEnabled(False)

    def _hide_add_form(self):
        if self._add_form:
            self._add_form.deleteLater()
            self._add_form = None
        self._add_btn.setEnabled(True)

    def _on_link_added(self, lnk: dict):
        self._hide_add_form()
        if lnk.get("_pending"):
            self._pending_links.append(lnk)
        self._links.append(lnk)
        self._add_link_row(lnk)
        self._update_empty_state()

    def _on_remove(self, link_id: int):
        # Remove from UI immediately
        for i in range(self._links_container.count()):
            item = self._links_container.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), LinkRow):
                if item.widget().link_id == link_id:
                    w = self._links_container.takeAt(i)
                    if w.widget():
                        w.widget().deleteLater()
                    break

        # Remove from internal list
        self._links = [l for l in self._links if l.get("id") != link_id]
        self._update_empty_state()

        # Delete from DB (only if it has a real id)
        if link_id is not None:
            dw = DeleteLinkWorker(link_id)
            dw.done.connect(lambda _: None)
            dw.error.connect(lambda _: None)
            dw.start()
            self._workers.append(dw)
