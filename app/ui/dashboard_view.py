"""
app/ui/dashboard_view.py
Zen AI — Dashboard (V3 — Premium Glassmorphic)

Shows:
  - Live stat cards (entity counts per type)
  - Top entities by importance score
  - System status (Ollama, FAISS index, DB)
  - Welcome hero banner
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QGridLayout, QPushButton,
    QSizePolicy, QSpacerItem, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import (
    Qt, QThread, Signal, QTimer,
    QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup,
    QParallelAnimationGroup, QSize
)
from PySide6.QtGui import QFont, QColor

from app.database.db_init import get_session
from app.database.models import (
    Universe, Character, Faction, Location,
    Event, Artifact, Story, RootEntity,
    RelationshipEdge, Power
)


# ─────────────────────────────────────────────────────────
# Background worker — DB stats fetch
# ─────────────────────────────────────────────────────────
class StatsWorker(QThread):
    data_ready = Signal(dict)
    error      = Signal(str)

    def run(self):
        try:
            session = get_session()
            stats = {
                "universes":     session.query(Universe).count(),
                "characters":    session.query(Character).count(),
                "factions":      session.query(Faction).count(),
                "locations":     session.query(Location).count(),
                "events":        session.query(Event).count(),
                "artifacts":     session.query(Artifact).count(),
                "stories":       session.query(Story).count(),
                "root_entities": session.query(RootEntity).count(),
                "relationships": session.query(RelationshipEdge).count(),
                "powers":        session.query(Power).count(),

                # Top characters by importance
                "top_characters": [
                    {"name": c.name, "score": c.importance_score,
                     "species": c.species or "—", "canon": c.canon_status}
                    for c in session.query(Character)
                                    .order_by(Character.importance_score.desc())
                                    .limit(5).all()
                ],

                # All universes (for quick list)
                "universes_list": [
                    {"name": u.name, "canon": u.canon_status,
                     "score": u.importance_score}
                    for u in session.query(Universe)
                                    .order_by(Universe.importance_score.desc())
                                    .limit(6).all()
                ],

                # Root entities
                "root_entities_list": [
                    {"name": r.name, "type": r.type or "Root", "score": r.importance_score}
                    for r in session.query(RootEntity)
                                    .order_by(RootEntity.importance_score.desc())
                                    .all()
                ],
            }

            # FAISS index size
            try:
                from app.search import faiss_store
                stats["faiss_vectors"] = faiss_store.index_size()
            except Exception:
                stats["faiss_vectors"] = -1

            # Ollama status — use configured URL, fall back to default
            try:
                import requests as _req
                from config.app_settings import get_app_settings
                _settings = get_app_settings()
                _ollama_base = getattr(_settings, "ollama_url", "http://localhost:11434").rstrip("/")
                r = _req.get(f"{_ollama_base}/api/tags", timeout=2)
                stats["ollama_online"] = r.status_code == 200
            except Exception:
                stats["ollama_online"] = False

            session.close()
            self.data_ready.emit(stats)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


# ─────────────────────────────────────────────────────────
# Animated Stat Card
# ─────────────────────────────────────────────────────────
class StatCard(QFrame):
    GRADIENTS = {
        "universes":     ("rgba(0,173,181,0.15)", "#00ADB5"),
        "characters":    ("rgba(199,125,255,0.15)", "#C77DFF"),
        "factions":      ("rgba(243,156,18,0.15)", "#f39c12"),
        "locations":     ("rgba(46,204,113,0.15)", "#2ecc71"),
        "events":        ("rgba(231,76,60,0.15)", "#e74c3c"),
        "artifacts":     ("rgba(241,196,15,0.15)", "#f1c40f"),
        "stories":       ("rgba(52,152,219,0.15)", "#3498db"),
        "root_entities": ("rgba(255,215,0,0.15)", "#FFD700"),
        "relationships": ("rgba(26,188,156,0.15)", "#1abc9c"),
        "powers":        ("rgba(233,30,99,0.15)", "#e91e63"),
    }
    ICONS = {
        "universes":     "🌐",
        "characters":    "👤",
        "factions":      "⚔",
        "locations":     "📍",
        "events":        "📅",
        "artifacts":     "💎",
        "stories":       "📖",
        "root_entities": "✦",
        "relationships": "🔗",
        "powers":        "⚡",
    }

    def __init__(self, key: str, label: str, value: int = 0):
        super().__init__()
        self.key   = key
        self._val  = value
        bg, color  = self.GRADIENTS.get(key, ("rgba(0,173,181,0.15)", "#00ADB5"))
        icon       = self.ICONS.get(key, "◈")

        self.setMinimumSize(170, 110)
        self.setMaximumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {bg}, stop:1 rgba(15,15,15,0.95)
                );
                border: 1px solid rgba(60,60,60,0.4);
                border-radius: 14px;
            }}
            QFrame:hover {{
                border: 1px solid {color}55;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {bg}, stop:0.4 rgba(25,25,25,0.95), stop:1 rgba(18,18,18,0.95)
                );
            }}
        """)

        # Subtle drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(2)

        # Icon + Label row
        top = QHBoxLayout()
        top.setSpacing(6)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"font-size: 10px; color: {color}; font-weight: 800; "
            "letter-spacing: 1.5px; background: transparent; border: none;"
        )
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            f"font-size: 20px; color: {color}; background: transparent; border: none;"
        )
        top.addWidget(lbl)
        top.addStretch()
        top.addWidget(icon_lbl)
        layout.addLayout(top)

        layout.addStretch()

        # Value
        self.value_lbl = QLabel(str(value))
        self.value_lbl.setStyleSheet(
            "font-size: 38px; font-weight: 900; color: #FFFFFF; "
            "background: transparent; border: none; letter-spacing: -1px;"
        )
        layout.addWidget(self.value_lbl)

    def set_value(self, v: int):
        self._val = v
        self.value_lbl.setText(str(v))


# ─────────────────────────────────────────────────────────
# Section header
# ─────────────────────────────────────────────────────────
def _section_header(text: str) -> QWidget:
    w = QWidget()
    w.setFixedHeight(34)
    w.setStyleSheet("background: transparent; border: none;")
    l = QHBoxLayout(w)
    l.setContentsMargins(0, 6, 0, 0)
    l.setSpacing(10)

    dot = QLabel("✦")
    dot.setStyleSheet("color: #00ADB5; font-size: 13px; font-weight: 900; background: transparent;")
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color: #555; font-size: 11px; font-weight: 800; "
        "letter-spacing: 3px; background: transparent;"
    )
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("background: #1A1A1A; border: none; max-height: 1px;")

    l.addWidget(dot)
    l.addWidget(lbl)
    l.addWidget(line, 1)
    return w


# ─────────────────────────────────────────────────────────
# Universe pill
# ─────────────────────────────────────────────────────────
def _universe_pill(data: dict) -> QFrame:
    canon_colors = {
        "canon":        "#00ADB5",
        "non_canon":    "#e74c3c",
        "alt_timeline": "#F39C12",
        "experimental": "#9B59B6",
    }
    c = canon_colors.get(data["canon"], "#00ADB5")
    f = QFrame()
    f.setFixedHeight(50)
    f.setStyleSheet(f"""
        QFrame {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(0,0,0,0), stop:0.02 {c}22, stop:1 rgba(18,18,18,0.95));
            border: 1px solid #1E1E1E;
            border-left: 3px solid {c};
            border-radius: 10px;
        }}
        QFrame:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(0,0,0,0), stop:0.05 {c}33, stop:1 rgba(28,28,28,0.95));
            border: 1px solid {c}44;
            border-left: 3px solid {c};
        }}
    """)
    lay = QHBoxLayout(f)
    lay.setContentsMargins(18, 0, 18, 0)

    name = QLabel(f"{data['name']}")
    name.setStyleSheet(
        "color: #EEEEEE; font-size: 13px; font-weight: 700; "
        "background: transparent; border: none;"
    )
    canon_tag = QLabel(data["canon"].upper().replace("_", " "))
    canon_tag.setStyleSheet(
        f"color: {c}; font-size: 9px; font-weight: 800; letter-spacing: 1px; "
        "background: transparent; border: none; padding: 2px 6px;"
    )
    score = QLabel(f"★ {data['score']}")
    score.setStyleSheet(
        f"color: {c}; font-size: 12px; font-weight: 800; "
        "background: transparent; border: none;"
    )
    lay.addWidget(name)
    lay.addWidget(canon_tag)
    lay.addStretch()
    lay.addWidget(score)
    return f


# ─────────────────────────────────────────────────────────
# Character row
# ─────────────────────────────────────────────────────────
def _char_row(data: dict) -> QFrame:
    f = QFrame()
    f.setFixedHeight(60)
    f.setStyleSheet("""
        QFrame {
            background: rgba(15, 15, 15, 0.9);
            border: 1px solid #1E1E1E;
            border-radius: 10px;
        }
        QFrame:hover {
            background: rgba(25, 25, 25, 0.9);
            border: 1px solid rgba(199,125,255,0.3);
        }
    """)
    lay = QHBoxLayout(f)
    lay.setContentsMargins(16, 0, 16, 0)
    lay.setSpacing(14)

    # Avatar circle
    avatar = QLabel("👤")
    avatar.setFixedSize(36, 36)
    avatar.setAlignment(Qt.AlignCenter)
    avatar.setStyleSheet(
        "background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #1E1E1E, stop:1 #151515); "
        "border-radius: 18px; font-size: 18px; border: 1px solid #2A2A2A;"
    )

    # Details
    det_lay = QVBoxLayout()
    det_lay.setSpacing(2)
    det_lay.setAlignment(Qt.AlignVCenter)
    name = QLabel(data['name'])
    name.setStyleSheet(
        "color: #FFFFFF; font-size: 13px; font-weight: 700; "
        "background: transparent; border: none;"
    )
    species = QLabel(data["species"])
    species.setStyleSheet(
        "color: #555; font-size: 11px; background: transparent; border: none;"
    )
    det_lay.addWidget(name)
    det_lay.addWidget(species)

    # Importance bar (smooth)
    bar_container = QFrame()
    bar_container.setFixedSize(100, 22)
    bar_container.setStyleSheet("background: transparent; border: none;")

    score_lbl = QLabel(f"{data['score']}", bar_container)
    score_lbl.setGeometry(0, 0, 100, 12)
    score_lbl.setAlignment(Qt.AlignRight)
    score_lbl.setStyleSheet(
        "color: #C77DFF; font-size: 10px; font-weight: 800; "
        "background: transparent;"
    )

    bar_bg = QFrame(bar_container)
    bar_bg.setGeometry(0, 14, 100, 5)
    bar_bg.setStyleSheet("background: #1A1A1A; border-radius: 2px;")

    bar_fill = QFrame(bar_container)
    fill_w = max(4, int(100 * data["score"] / 100))
    bar_fill.setGeometry(0, 14, fill_w, 5)
    bar_fill.setStyleSheet(
        "background: qlineargradient(x1:0,y1:0,x2:1,y2:0, "
        "stop:0 #8e44ad, stop:1 #C77DFF); border-radius: 2px;"
    )

    lay.addWidget(avatar)
    lay.addLayout(det_lay)
    lay.addStretch()
    lay.addWidget(bar_container)
    return f


# ─────────────────────────────────────────────────────────
# Status indicator
# ─────────────────────────────────────────────────────────
def _status_dot(online: bool, label: str) -> QFrame:
    f = QFrame()
    f.setFixedHeight(38)
    c = "#2ecc71" if online else "#e74c3c"
    f.setStyleSheet(f"""
        QFrame {{
            background: rgba(15,15,15,0.8);
            border: 1px solid #1A1A1A;
            border-radius: 8px;
        }}
        QFrame:hover {{ border-color: {c}44; }}
    """)
    lay = QHBoxLayout(f)
    lay.setContentsMargins(14, 0, 14, 0)
    lay.setSpacing(10)

    dot = QLabel("●")
    dot.setStyleSheet(
        f"color: {c}; font-size: 14px; background: transparent; border: none;"
    )
    # Glow effect
    shadow = QGraphicsDropShadowEffect(dot)
    shadow.setBlurRadius(12)
    shadow.setColor(QColor(c))
    shadow.setOffset(0)
    dot.setGraphicsEffect(shadow)

    lbl = QLabel(label)
    lbl.setStyleSheet(
        "color: #888; font-size: 12px; font-weight: 600; "
        "background: transparent; border: none;"
    )
    lay.addWidget(dot)
    lay.addWidget(lbl)
    lay.addStretch()
    return f


# ─────────────────────────────────────────────────────────
# Hero Welcome Banner
# ─────────────────────────────────────────────────────────
def _hero_banner() -> QFrame:
    f = QFrame()
    f.setFixedHeight(100)
    f.setStyleSheet("""
        QFrame {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(0,173,181,0.08), stop:0.5 rgba(142,68,173,0.06), stop:1 rgba(0,0,0,0));
            border: 1px solid #1A1A1A;
            border-radius: 16px;
        }
    """)
    lay = QVBoxLayout(f)
    lay.setContentsMargins(28, 20, 28, 20)
    lay.setSpacing(6)

    greeting = QLabel("Welcome back, Creator.")
    greeting.setStyleSheet(
        "color: #EEEEEE; font-size: 22px; font-weight: 900; "
        "letter-spacing: 1px; background: transparent; border: none;"
    )

    sub = QLabel("Your multiverse awaits. All systems are being monitored.")
    sub.setStyleSheet(
        "color: #444; font-size: 12px; font-weight: 600; "
        "letter-spacing: 0.5px; background: transparent; border: none;"
    )

    lay.addWidget(greeting)
    lay.addWidget(sub)
    return f


# ─────────────────────────────────────────────────────────
# Main Dashboard Widget
# ─────────────────────────────────────────────────────────
class DashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._worker = None
        self._cards  = {}
        self._setup_ui()

        # Defer first data load to after the UI is shown (smoother startup)
        QTimer.singleShot(100, self._refresh)

        # Auto-refresh every 90 seconds (reduced from 60 for less overhead)
        self._timer = QTimer(self)
        self._timer.setInterval(90_000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()

    # ── Build UI ──────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──
        top_bar = QFrame()
        top_bar.setFixedHeight(58)
        top_bar.setStyleSheet(
            "background: rgba(13,13,13,0.95); border-bottom: 1px solid #151515;"
        )
        bar_lay = QHBoxLayout(top_bar)
        bar_lay.setContentsMargins(32, 0, 32, 0)

        title = QLabel("◈  Dashboard")
        title.setStyleSheet(
            "color: #00ADB5; font-size: 18px; font-weight: 900; "
            "letter-spacing: 2px; background: transparent; border: none;"
        )
        self.refresh_btn = QPushButton("↻  Refresh")
        self.refresh_btn.setFixedHeight(32)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #444;
                border: 1px solid #1E1E1E;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover { color: #00ADB5; border-color: #00ADB544; }
        """)
        self.refresh_btn.clicked.connect(self._refresh)

        self.status_lbl = QLabel("●  Loading...")
        self.status_lbl.setStyleSheet(
            "color: #333; font-size: 11px; background: transparent; border: none;"
        )

        bar_lay.addWidget(title)
        bar_lay.addStretch()
        bar_lay.addWidget(self.status_lbl)
        bar_lay.addSpacing(12)
        bar_lay.addWidget(self.refresh_btn)

        root.addWidget(top_bar)

        # ── Scrollable content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: #0D0D0D; }
            QScrollBar:vertical {
                background: #0D0D0D; width: 6px; border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #222; border-radius: 3px; min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #00ADB5; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        content = QWidget()
        content.setStyleSheet("background: #0D0D0D;")
        self._content_lay = QVBoxLayout(content)
        self._content_lay.setContentsMargins(32, 24, 32, 40)
        self._content_lay.setSpacing(22)

        # ── Hero Banner ──
        self._content_lay.addWidget(_hero_banner())

        # ── Stat cards grid ──
        self._content_lay.addWidget(_section_header("MULTIVERSE AT A GLANCE"))
        self._cards_grid = QGridLayout()
        self._cards_grid.setSpacing(14)
        self._build_stat_cards()
        self._content_lay.addLayout(self._cards_grid)

        # ── Bottom columns ──
        cols = QHBoxLayout()
        cols.setSpacing(24)

        # Left: Universes
        left = QVBoxLayout()
        left.setSpacing(8)
        left.addWidget(_section_header("UNIVERSES"))
        self._universe_col = QVBoxLayout()
        self._universe_col.setSpacing(6)
        left.addLayout(self._universe_col)
        left.addStretch()

        # Middle: Top Characters
        mid = QVBoxLayout()
        mid.setSpacing(8)
        mid.addWidget(_section_header("TOP CHARACTERS"))
        self._char_col = QVBoxLayout()
        self._char_col.setSpacing(6)
        mid.addLayout(self._char_col)
        mid.addStretch()

        # Right: System Status + Root Entities
        right = QVBoxLayout()
        right.setSpacing(8)
        right.addWidget(_section_header("SYSTEM STATUS"))
        self._status_col = QVBoxLayout()
        self._status_col.setSpacing(6)
        right.addLayout(self._status_col)
        right.addSpacing(16)
        right.addWidget(_section_header("ROOT ENTITIES"))
        self._root_col = QVBoxLayout()
        self._root_col.setSpacing(6)
        right.addLayout(self._root_col)
        right.addStretch()

        cols.addLayout(left, 3)
        cols.addLayout(mid, 4)
        cols.addLayout(right, 3)
        self._content_lay.addLayout(cols)
        self._content_lay.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    def _build_stat_cards(self):
        CARDS = [
            ("universes",     "UNIVERSES"),
            ("characters",    "CHARACTERS"),
            ("factions",      "FACTIONS"),
            ("locations",     "LOCATIONS"),
            ("events",        "EVENTS"),
            ("artifacts",     "ARTIFACTS"),
            ("stories",       "STORIES"),
            ("root_entities", "ROOT ENTITIES"),
            ("relationships", "RELATIONSHIPS"),
            ("powers",        "POWERS"),
        ]
        for i, (key, label) in enumerate(CARDS):
            card = StatCard(key, label, 0)
            self._cards[key] = card
            self._cards_grid.addWidget(card, i // 5, i % 5)

    # ── Refresh ───────────────────────────────────────────

    def _refresh(self):
        if self._worker and self._worker.isRunning():
            return  # Don't stack workers
        self.status_lbl.setText("●  Refreshing...")
        self.status_lbl.setStyleSheet(
            "color: #00ADB5; font-size: 11px; background: transparent; border: none;"
        )
        self.refresh_btn.setEnabled(False)
        self._worker = StatsWorker()
        self._worker.data_ready.connect(self._on_data)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_data(self, data: dict):
        # Update stat cards
        for key, card in self._cards.items():
            card.set_value(data.get(key, 0))

        # Universes list
        self._clear_layout(self._universe_col)
        unis = data.get("universes_list", [])
        if unis:
            for u in unis:
                self._universe_col.addWidget(_universe_pill(u))
        else:
            self._universe_col.addWidget(self._empty_label("Koi universe nahi"))

        # Characters
        self._clear_layout(self._char_col)
        chars = data.get("top_characters", [])
        if chars:
            for c in chars:
                self._char_col.addWidget(_char_row(c))
        else:
            self._char_col.addWidget(self._empty_label("Koi character nahi"))

        # System status
        self._clear_layout(self._status_col)
        ollama_ok = data.get("ollama_online", False)
        faiss_n   = data.get("faiss_vectors", 0)
        self._status_col.addWidget(
            _status_dot(ollama_ok,
                        f"Ollama  {'(Online)' if ollama_ok else '(Offline)'}")
        )
        self._status_col.addWidget(
            _status_dot(faiss_n > 0,
                        f"FAISS Index  ({faiss_n} vectors)")
        )
        self._status_col.addWidget(
            _status_dot(True, "SQLite DB  (Connected)")
        )

        # Root Entities
        self._clear_layout(self._root_col)
        roots = data.get("root_entities_list", [])
        if roots:
            for r in roots:
                row = QFrame()
                row.setFixedHeight(34)
                row.setStyleSheet("""
                    QFrame {
                        background: rgba(255,215,0,0.04);
                        border: 1px solid #1A1A1A;
                        border-radius: 6px;
                    }
                    QFrame:hover { border-color: #FFD70033; }
                """)
                rl = QHBoxLayout(row)
                rl.setContentsMargins(12, 0, 12, 0)
                n_lbl = QLabel(f"✦  {r['name']}")
                n_lbl.setStyleSheet(
                    "color: #FFD700; font-size: 12px; font-weight: 700; "
                    "background: transparent; border: none;"
                )
                t_lbl = QLabel(r['type'])
                t_lbl.setStyleSheet(
                    "color: #555; font-size: 10px; font-weight: 600; "
                    "background: transparent; border: none;"
                )
                rl.addWidget(n_lbl)
                rl.addStretch()
                rl.addWidget(t_lbl)
                self._root_col.addWidget(row)
        else:
            self._root_col.addWidget(self._empty_label("Koi root entity nahi"))

        total = sum(
            data.get(k, 0)
            for k in ("universes", "characters", "factions", "locations",
                      "events", "artifacts", "stories")
        )
        self.status_lbl.setText(f"●  {total} total entities")
        self.status_lbl.setStyleSheet(
            "color: #2ecc71; font-size: 11px; background: transparent; border: none;"
        )
        self.refresh_btn.setEnabled(True)

    def _on_error(self, msg: str):
        self.status_lbl.setText(f"●  Error: {msg}")
        self.status_lbl.setStyleSheet(
            "color: #e74c3c; font-size: 11px; background: transparent; border: none;"
        )
        self.refresh_btn.setEnabled(True)

    # ── Helpers ───────────────────────────────────────────

    @staticmethod
    def _clear_layout(lay):
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    @staticmethod
    def _empty_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color: #2A2A2A; font-size: 13px; padding: 10px 0; "
            "background: transparent; border: none;"
        )
        return lbl
