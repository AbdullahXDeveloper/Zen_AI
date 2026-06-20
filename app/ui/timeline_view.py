"""
app/ui/timeline_view.py
Module 8b — Timeline View
Timeline engine (Module 4) ka data PySide6 mein scrollable visual list ke roop mein dikhata hai.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QFrame, QPushButton, QComboBox, QSizePolicy,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor

from app.database.db_init import get_session
from app.database.models import Universe, Character
from app.timeline.engine import get_timeline


# ─────────────────────────────────────────────
# Background thread: timeline data fetch karo
# ─────────────────────────────────────────────
class TimelineWorker(QThread):
    data_ready = Signal(list)
    error = Signal(str)

    def __init__(self, scope, entity_id=None):
        super().__init__()
        self.scope = scope
        self.entity_id = entity_id

    def run(self):
        try:
            session = get_session()
            data = get_timeline(session, scope=self.scope, entity_id=self.entity_id)
            self.data_ready.emit(data)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            session.close()


# ─────────────────────────────────────────────
# Single event card
# ─────────────────────────────────────────────
class TimelineCard(QFrame):
    # Color mapping for event types
    TYPE_COLORS = {
        "birth":   ("#2ecc71", "🟢"),
        "death":   ("#e74c3c", "🔴"),
        "rebirth": ("#9b59b6", "🟣"),
        "war":     ("#e67e22", "🟠"),
        "other":   ("#00ADB5", "🔵"),
    }
    CANON_BADGE = {
        "canon":        ("#00ADB5", "CANON"),
        "non_canon":    ("#e74c3c", "NON-CANON"),
        "alt_timeline": ("#9b59b6", "ALT"),
        "experimental": ("#f39c12", "EXPERIMENTAL"),
    }

    def __init__(self, event_data: dict, is_right: bool = False):
        super().__init__()
        self._build(event_data, is_right)

    def _build(self, e: dict, is_right: bool):
        self.setObjectName("TimelineCard")
        color, icon = self.TYPE_COLORS.get(e.get("event_type", "other"), ("#00ADB5", "🔵"))
        canon_color, canon_text = self.CANON_BADGE.get(
            e.get("canon_status", "canon"), ("#00ADB5", "CANON")
        )
        importance = e.get("importance_score", 0) or 0

        self.setStyleSheet(f"""
            QFrame#TimelineCard {{
                background-color: #141414;
                border: 1px solid #222222;
                border-left: 3px solid {color};
                border-radius: 8px;
            }}
            QFrame#TimelineCard:hover {{
                background-color: #1A1A1A;
                border-left: 3px solid {color};
            }}
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # ── Header row ──
        header = QHBoxLayout()
        header.setSpacing(8)

        # Date badge
        date_text = e.get("date_label") or str(e.get("date_value") or "Unknown Date")
        date_lbl = QLabel(date_text)
        date_lbl.setStyleSheet(f"""
            background-color: {color}22;
            color: {color};
            border: 1px solid {color}55;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: 700;
        """)

        # Event name
        name_lbl = QLabel(f"{icon}  {e.get('name', 'Unnamed Event')}")
        name_lbl.setStyleSheet(
            "color: #EEEEEE; font-size: 14px; font-weight: 700; background: transparent; border: none;"
        )
        name_lbl.setWordWrap(True)

        # Canon badge
        canon_badge = QLabel(canon_text)
        canon_badge.setStyleSheet(f"""
            background-color: {canon_color}22;
            color: {canon_color};
            border: 1px solid {canon_color}55;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 10px;
            font-weight: 700;
        """)

        # Importance
        imp_bar = self._make_importance_bar(importance, color)

        header.addWidget(date_lbl)
        header.addWidget(name_lbl, 1)
        header.addWidget(canon_badge)
        header.addWidget(imp_bar)
        layout.addLayout(header)

        # ── Description ──
        desc = e.get("description", "")
        if desc:
            desc_lbl = QLabel(desc[:220] + ("..." if len(desc) > 220 else ""))
            desc_lbl.setStyleSheet(
                "color: #777777; font-size: 12px; background: transparent; border: none;"
            )
            desc_lbl.setWordWrap(True)
            layout.addWidget(desc_lbl)

        # ── Participants ──
        refs = e.get("entity_refs", [])
        if refs:
            ref_row = QHBoxLayout()
            ref_row.setSpacing(6)
            prefix_icon = {"character": "👤", "faction": "⚔", "location": "📍", "artifact": "💎"}
            for r in refs[:5]:
                ptype = r.get("type", "")
                ic = prefix_icon.get(ptype, "•")
                role = r.get("role") or ptype
                tag = QLabel(f"{ic} {role}")
                tag.setStyleSheet("""
                    color: #555555;
                    font-size: 11px;
                    background: #1E1E1E;
                    border: 1px solid #2A2A2A;
                    border-radius: 3px;
                    padding: 1px 6px;
                """)
                ref_row.addWidget(tag)
            if len(refs) > 5:
                more = QLabel(f"+{len(refs)-5} more")
                more.setStyleSheet("color: #444; font-size: 11px;")
                ref_row.addWidget(more)
            ref_row.addStretch()
            layout.addLayout(ref_row)

    def _make_importance_bar(self, score: int, color: str) -> QWidget:
        container = QFrame()
        container.setFixedSize(60, 20)
        container.setStyleSheet("background: transparent; border: none;")
        inner = QFrame(container)
        fill_w = max(2, int(60 * score / 100))
        inner.setGeometry(0, 7, fill_w, 6)
        inner.setStyleSheet(f"background: {color}88; border-radius: 3px;")
        bg = QFrame(container)
        bg.setGeometry(0, 7, 60, 6)
        bg.setStyleSheet("background: #222; border-radius: 3px;")
        bg.lower()
        score_lbl = QLabel(str(score), container)
        score_lbl.setGeometry(0, 0, 60, 8)
        score_lbl.setAlignment(Qt.AlignRight)
        score_lbl.setStyleSheet("color: #444; font-size: 9px; background: transparent;")
        return container


# ─────────────────────────────────────────────
# Main Timeline View Widget
# ─────────────────────────────────────────────
class TimelineViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._worker = None
        self._all_events = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Control Bar ──
        bar = QFrame()
        bar.setFixedHeight(60)
        bar.setStyleSheet(
            "background-color: #111111; border-bottom: 1px solid #222222;"
        )
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(20, 0, 20, 0)
        bar_layout.setSpacing(12)

        # Scope selector
        scope_label = QLabel("Scope:")
        scope_label.setStyleSheet("color: #888; font-size: 13px;")
        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["Multiverse", "Universe", "Character"])
        self.scope_combo.setStyleSheet(_combo_style())
        self.scope_combo.currentIndexChanged.connect(self._on_scope_changed)

        # Entity selector
        self.entity_label = QLabel("Universe:")
        self.entity_label.setStyleSheet("color: #888; font-size: 13px;")
        self.entity_combo = QComboBox()
        self.entity_combo.setMinimumWidth(200)
        self.entity_combo.setStyleSheet(_combo_style())
        self.entity_frame = QFrame()
        ef = QHBoxLayout(self.entity_frame)
        ef.setContentsMargins(0, 0, 0, 0)
        ef.setSpacing(8)
        ef.addWidget(self.entity_label)
        ef.addWidget(self.entity_combo)
        self.entity_frame.hide()

        # Canon filter
        filter_label = QLabel("Canon:")
        filter_label.setStyleSheet("color: #888; font-size: 13px;")
        self.canon_combo = QComboBox()
        self.canon_combo.addItems(["All", "canon", "non_canon", "alt_timeline", "experimental"])
        self.canon_combo.setStyleSheet(_combo_style())
        self.canon_combo.currentIndexChanged.connect(self._apply_filter)

        # Load button
        self.load_btn = QPushButton("⏱  Load Timeline")
        self.load_btn.setFixedHeight(36)
        self.load_btn.setStyleSheet(_btn_style())
        self.load_btn.clicked.connect(self._load_timeline)

        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #444; font-size: 12px;")

        bar_layout.addWidget(scope_label)
        bar_layout.addWidget(self.scope_combo)
        bar_layout.addWidget(self.entity_frame)
        bar_layout.addWidget(filter_label)
        bar_layout.addWidget(self.canon_combo)
        bar_layout.addStretch()
        bar_layout.addWidget(self.status_label)
        bar_layout.addWidget(self.load_btn)

        # ── Scroll Area ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: #0D0D0D; }
            QScrollBar:vertical {
                background: #111; width: 6px; border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #333; border-radius: 3px; min-height: 20px;
            }
        """)

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: #0D0D0D;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(40, 30, 40, 40)
        self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch()

        scroll.setWidget(self.cards_container)

        root.addWidget(bar)
        root.addWidget(scroll)

        # Init
        self._on_scope_changed(0)
        self._show_empty("Scope choose karein aur Load dabayein")

    # ── Helpers ──────────────────────────────

    def _show_empty(self, msg="Koi events nahi mile"):
        self._clear_cards()
        lbl = QLabel(msg)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #333; font-size: 16px; padding: 60px;")
        self.cards_layout.insertWidget(0, lbl)

    def _clear_cards(self):
        while self.cards_layout.count() > 1:  # stretch rehne do
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _populate_entity_combo(self, scope):
        self.entity_combo.clear()
        try:
            session = get_session()
            if scope == "universe":
                items = session.query(Universe).order_by(Universe.name).all()
                self.entity_label.setText("Universe:")
                for item in items:
                    self.entity_combo.addItem(f"{item.name} (ID: {item.id})", item.id)
            elif scope == "character":
                items = session.query(Character).order_by(Character.name).all()
                self.entity_label.setText("Character:")
                for item in items:
                    self.entity_combo.addItem(f"{item.name} (ID: {item.id})", item.id)
        except Exception as e:
            self.entity_combo.addItem(f"Error: {e}")
        finally:
            session.close()

    def _render_events(self, events: list):
        self._clear_cards()
        if not events:
            self._show_empty("Is scope mein koi events nahi hain")
            return

        # ── Header ──
        header = QLabel(f"  {len(events)} Events  •  Chronological Order")
        header.setStyleSheet(
            "color: #00ADB5; font-size: 12px; font-weight: 700; "
            "letter-spacing: 2px; padding-bottom: 8px; background: transparent;"
        )
        self.cards_layout.insertWidget(0, header)

        for i, event in enumerate(events):
            card = TimelineCard(event, is_right=(i % 2 == 1))
            self.cards_layout.insertWidget(i + 1, card)

    # ── Slots ─────────────────────────────────

    def _on_scope_changed(self, index):
        scope_map = {0: "multiverse", 1: "universe", 2: "character"}
        scope = scope_map.get(index, "multiverse")
        needs_entity = scope in ("universe", "character")
        self.entity_frame.setVisible(needs_entity)
        if needs_entity:
            self._populate_entity_combo(scope)

    def _apply_filter(self):
        """Canon filter apply karo already loaded events par."""
        canon_filter = self.canon_combo.currentText()
        if not self._all_events:
            return
        if canon_filter == "All":
            filtered = self._all_events
        else:
            filtered = [e for e in self._all_events if e.get("canon_status") == canon_filter]
        self._render_events(filtered)
        self.status_label.setText(f"Showing {len(filtered)} events")

    def _load_timeline(self):
        scope_map = {0: "multiverse", 1: "universe", 2: "character"}
        idx = self.scope_combo.currentIndex()
        scope = scope_map.get(idx, "multiverse")

        entity_id = None
        if scope != "multiverse":
            entity_id = self.entity_combo.currentData()
            if entity_id is None:
                self.status_label.setText("⚠ Pehle entity choose karein")
                return

        self.load_btn.setEnabled(False)
        self.status_label.setText("Loading...")
        self._show_empty("Timeline load ho rahi hai...")

        self._worker = TimelineWorker(scope, entity_id)
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_data_ready(self, events: list):
        self._all_events = events
        self.load_btn.setEnabled(True)
        self._apply_filter()

    def _on_error(self, msg: str):
        self.status_label.setText(f"Error")
        self.load_btn.setEnabled(True)
        self._show_empty(f"⚠ Error: {msg}")


# ─────────────────────────────────────────────
# Style helpers
# ─────────────────────────────────────────────
def _combo_style():
    return """
        QComboBox {
            background-color: #1A1A1A;
            color: #CCCCCC;
            border: 1px solid #333333;
            border-radius: 5px;
            padding: 5px 10px;
            font-size: 13px;
        }
        QComboBox:hover { border-color: #00ADB5; }
        QComboBox QAbstractItemView {
            background-color: #1A1A1A;
            color: #CCCCCC;
            selection-background-color: #00ADB5;
        }
    """

def _btn_style():
    return """
        QPushButton {
            background-color: #00ADB5;
            color: #000000;
            border: none;
            border-radius: 6px;
            padding: 0 18px;
            font-size: 13px;
            font-weight: 700;
        }
        QPushButton:hover { background-color: #00C9D4; }
        QPushButton:disabled { background-color: #1A3A3A; color: #555; }
    """
