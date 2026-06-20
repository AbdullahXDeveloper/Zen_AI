"""
app/ui/analytics_view.py
Zen AI — Analytics Page (Module 10 Frontend)
Theme: Multi-color charts, dark background
- Entity counts per type (bar)
- Canon status breakdown (pie-style)
- Top universes by entity count
- Importance score distribution
- All rendered as pure PySide6 (no Plotly/WebEngine needed)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QPushButton, QGridLayout
)
from PySide6.QtCore import Qt, QThread, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient

from app.database.db_init import get_session
from app.database import crud

ACCENT = "#00ADB5"

ENTITY_COLORS = {
    "Universes":  "#00ADB5",
    "Characters": "#9b59b6",
    "Factions":   "#f39c12",
    "Locations":  "#2ecc71",
    "Events":     "#e74c3c",
    "Artifacts":  "#00BCD4",
    "Stories":    "#8e44ad",
}


# ─── Worker ─────────────────────────────────────────────
class LoadAnalyticsWorker(QThread):
    done  = Signal(dict)
    error = Signal(str)

    def run(self):
        try:
            session = get_session()
            stats = {
                "universes":  len(crud.list_universes(session)),
                "characters": len(crud.list_characters(session)),
                "factions":   len(crud.list_factions(session)),
                "locations":  len(crud.list_locations(session)),
                "events":     len(crud.list_events(session)),
                "artifacts":  len(crud.list_artifacts(session)),
                "stories":    len(crud.list_stories(session)),
            }
            # Canon breakdown for characters
            canon_stats = {}
            for cs in ["canon", "non_canon", "alt_timeline", "experimental"]:
                canon_stats[cs] = len(crud.list_characters(session, canon_status=cs))

            # Top 5 universes by character count
            unis = crud.list_universes(session)
            top_unis = []
            for u in unis:
                char_count = len(crud.list_characters(session, universe_id=u.id))
                fac_count  = len(crud.list_factions(session, universe_id=u.id))
                loc_count  = len(crud.list_locations(session, universe_id=u.id))
                top_unis.append({
                    "name": u.name,
                    "chars": char_count,
                    "factions": fac_count,
                    "locations": loc_count,
                    "total": char_count + fac_count + loc_count,
                })
            top_unis.sort(key=lambda x: x["total"], reverse=True)

            session.close()
            self.done.emit({
                "entity_counts": stats,
                "canon_stats": canon_stats,
                "top_universes": top_unis[:5],
            })
        except Exception as e:
            self.error.emit(str(e))


# ─── Stat Card ──────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, label: str, value: int, color: str):
        super().__init__()
        self.setFixedHeight(90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(f"""
            QFrame {{
                background: #111111;
                border: 1px solid #1E1E1E;
                border-top: 3px solid {color};
                border-radius: 10px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(4)

        val_lbl = QLabel(str(value))
        val_lbl.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: 900; background: transparent; border: none;")

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #444; font-size: 11px; font-weight: 600; letter-spacing: 1px; background: transparent; border: none;")

        lay.addWidget(val_lbl)
        lay.addWidget(lbl)


# ─── Horizontal Bar Chart ────────────────────────────────
class HBarChart(QFrame):
    """Simple horizontal bar chart drawn with QPainter."""

    def __init__(self, data: list[tuple], title: str):
        """data = [(label, value, color), ...]"""
        super().__init__()
        self.data  = data
        self.title = title
        self.setMinimumHeight(max(180, len(data) * 40 + 60))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setStyleSheet("background: #111111; border: 1px solid #1E1E1E; border-radius: 10px;")

    def paintEvent(self, event):
        if not self.data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        W, H   = self.width(), self.height()
        pad_l  = 130  # label area
        pad_r  = 60
        pad_t  = 40
        pad_b  = 20
        bar_h  = 22
        gap    = 14
        max_val = max(v for _, v, _ in self.data) or 1

        # Title
        p.setPen(QColor("#444444"))
        f = QFont()
        f.setPixelSize(11)
        f.setBold(True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        p.setFont(f)
        p.drawText(pad_l, 22, self.title.upper())

        chart_w = W - pad_l - pad_r

        for i, (label, value, color) in enumerate(self.data):
            y = pad_t + i * (bar_h + gap)

            # Label
            p.setPen(QColor("#666666"))
            f2 = QFont()
            f2.setPixelSize(11)
            p.setFont(f2)
            p.drawText(10, y + bar_h - 4, label[:16])

            # Bar background
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#1A1A1A"))
            p.drawRoundedRect(QRectF(pad_l, y, chart_w, bar_h), 4, 4)

            # Bar fill
            bar_w = int(chart_w * value / max_val)
            if bar_w > 0:
                c = QColor(color)
                grad = QLinearGradient(pad_l, 0, pad_l + bar_w, 0)
                grad.setColorAt(0, c)
                grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 120))
                p.setBrush(grad)
                p.drawRoundedRect(QRectF(pad_l, y, bar_w, bar_h), 4, 4)

            # Value label
            p.setPen(QColor("#888888"))
            f3 = QFont()
            f3.setPixelSize(11)
            f3.setBold(True)
            p.setFont(f3)
            p.drawText(pad_l + bar_w + 8, y + bar_h - 4, str(value))

        p.end()


# ─── Main Analytics View ─────────────────────────────────
class AnalyticsViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._worker = None
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.setStyleSheet("background: #0D0D0D;")

        # ── Top bar ──
        top_bar = QFrame()
        top_bar.setFixedHeight(64)
        top_bar.setStyleSheet("background: #0D0D0D; border-bottom: 1px solid #1A1A1A;")
        bar_lay = QHBoxLayout(top_bar)
        bar_lay.setContentsMargins(32, 0, 32, 0)

        title = QLabel("📊  Analytics")
        title.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: 900; letter-spacing: 2px; background: transparent; border: none;")
        self._refresh_btn = QPushButton("↻  Refresh")
        self._refresh_btn.setFixedHeight(32)
        self._refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {ACCENT};
                border: 1px solid {ACCENT}44; border-radius: 7px;
                padding: 0 16px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {ACCENT}14; border-color: {ACCENT}; }}
        """)
        self._refresh_btn.clicked.connect(self._load)
        bar_lay.addWidget(title)
        bar_lay.addStretch()
        bar_lay.addWidget(self._refresh_btn)
        lay.addWidget(top_bar)

        # ── Scroll content ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: #0D0D0D; } QScrollBar:vertical { background: #111; width: 6px; } QScrollBar::handle:vertical { background: #2A2A2A; border-radius: 3px; }")

        self._content = QWidget()
        self._content.setStyleSheet("background: #0D0D0D;")
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(32, 28, 32, 40)
        self._content_lay.setSpacing(24)

        self._loading_lbl = QLabel("Loading analytics...")
        self._loading_lbl.setAlignment(Qt.AlignCenter)
        self._loading_lbl.setStyleSheet("color: #222; font-size: 16px; padding: 80px; background: transparent; border: none;")
        self._content_lay.addWidget(self._loading_lbl)
        self._content_lay.addStretch()

        self._scroll.setWidget(self._content)
        lay.addWidget(self._scroll)

    def _load(self):
        self._refresh_btn.setEnabled(False)
        self._worker = LoadAnalyticsWorker()
        self._worker.done.connect(self._on_data)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _clear_content(self):
        while self._content_lay.count():
            item = self._content_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_data(self, data: dict):
        self._refresh_btn.setEnabled(True)
        self._clear_content()
        counts    = data["entity_counts"]
        canon     = data["canon_stats"]
        top_unis  = data["top_universes"]
        total     = sum(counts.values())

        # ── Section: Summary Cards ──
        self._content_lay.addWidget(self._section_header("MULTIVERSE OVERVIEW"))

        grid = QGridLayout()
        grid.setSpacing(14)
        cards = [
            ("TOTAL ENTITIES", total, ACCENT),
            ("UNIVERSES",  counts["universes"],  ENTITY_COLORS["Universes"]),
            ("CHARACTERS", counts["characters"], ENTITY_COLORS["Characters"]),
            ("FACTIONS",   counts["factions"],   ENTITY_COLORS["Factions"]),
            ("LOCATIONS",  counts["locations"],  ENTITY_COLORS["Locations"]),
            ("EVENTS",     counts["events"],     ENTITY_COLORS["Events"]),
            ("ARTIFACTS",  counts["artifacts"],  ENTITY_COLORS["Artifacts"]),
            ("STORIES",    counts["stories"],    ENTITY_COLORS["Stories"]),
        ]
        for i, (label, value, color) in enumerate(cards):
            card = StatCard(label, value, color)
            grid.addWidget(card, i // 4, i % 4)
        grid_w = QWidget()
        grid_w.setStyleSheet("background: transparent;")
        grid_w.setLayout(grid)
        self._content_lay.addWidget(grid_w)

        # ── Section: Entity Distribution ──
        self._content_lay.addWidget(self._section_header("ENTITY DISTRIBUTION"))
        entity_data = [
            (k.title(), v, ENTITY_COLORS.get(k.title(), ACCENT))
            for k, v in counts.items() if k != "universes"
        ]
        entity_data.sort(key=lambda x: x[1], reverse=True)
        bar1 = HBarChart(entity_data, "Entities per Type")
        self._content_lay.addWidget(bar1)

        # ── Section: Canon Status ──
        self._content_lay.addWidget(self._section_header("CHARACTER CANON STATUS"))
        canon_colors = {
            "canon": "#00ADB5", "non_canon": "#e74c3c",
            "alt_timeline": "#9b59b6", "experimental": "#f39c12"
        }
        canon_data = [
            (k.replace("_", " ").title(), v, canon_colors.get(k, ACCENT))
            for k, v in canon.items()
        ]
        bar2 = HBarChart(canon_data, "Characters by Canon Status")
        self._content_lay.addWidget(bar2)

        # ── Section: Top Universes ──
        if top_unis:
            self._content_lay.addWidget(self._section_header("TOP UNIVERSES  (by entity count)"))
            uni_data = [
                (u["name"], u["total"], ENTITY_COLORS["Universes"])
                for u in top_unis
            ]
            bar3 = HBarChart(uni_data, "Entities per Universe")
            self._content_lay.addWidget(bar3)

            # Detail table
            for u in top_unis[:5]:
                row = self._uni_row(u)
                self._content_lay.addWidget(row)

        self._content_lay.addStretch()

    def _on_error(self, msg: str):
        self._refresh_btn.setEnabled(True)
        self._clear_content()
        err = QLabel(f"Error: {msg}")
        err.setAlignment(Qt.AlignCenter)
        err.setStyleSheet("color: #e74c3c; font-size: 14px; padding: 60px; background: transparent; border: none;")
        self._content_lay.addWidget(err)

    def _section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #2A2A2A; font-size: 10px; font-weight: 700; letter-spacing: 3px; background: transparent; border: none; padding-top: 8px;")
        return lbl

    def _uni_row(self, u: dict) -> QFrame:
        row = QFrame()
        row.setFixedHeight(44)
        row.setStyleSheet("background: #0D0D0D; border: none;")
        r_lay = QHBoxLayout(row)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(24)

        name_lbl = QLabel(f"🌐  {u['name']}")
        name_lbl.setStyleSheet("color: #555; font-size: 13px; font-weight: 600; background: transparent; border: none;")
        name_lbl.setFixedWidth(200)

        def _chip(label, val, color):
            c = QLabel(f"{label}: {val}")
            c.setStyleSheet(
                f"color: {color}; font-size: 11px; "
                f"background: {color}12; border: 1px solid {color}33; "
                "border-radius: 4px; padding: 2px 10px;"
            )
            return c

        r_lay.addWidget(name_lbl)
        r_lay.addWidget(_chip("👤", u["chars"],    ENTITY_COLORS["Characters"]))
        r_lay.addWidget(_chip("⚔",  u["factions"], ENTITY_COLORS["Factions"]))
        r_lay.addWidget(_chip("📍", u["locations"], ENTITY_COLORS["Locations"]))
        r_lay.addStretch()
        return row
