"""
app/ui/main_window.py
Zen AI — Main Window (Updated: Module 8b)
Graph View (Module 3) aur Timeline View (Module 4) ab integrate ho gaye hain.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon
from pathlib import Path

_LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.jpg"
from app.ui.wiki_view import WikiViewWidget
from app.ui.ai_chat_view import AIChatWidget
from app.ui.graph_view import GraphViewWidget        # ← Module 8b: Graph
from app.ui.timeline_view import TimelineViewWidget  # ← Module 8b: Timeline
from app.ui.dashboard_view import DashboardWidget    # ← Phase 9A: Dashboard
from app.ui.universes_view import UniversesViewWidget    # ← Phase 9B: Universes
from app.ui.root_entities_view import RootEntitiesViewWidget # ← Phase 9B-2: Root Entities
from app.ui.characters_view import CharactersViewWidget  # ← Phase 9C: Characters
from app.ui.factions_view import FactionsViewWidget      # ← Phase 9D: Factions
from app.ui.locations_view import LocationsViewWidget    # ← Phase 9E: Locations
from app.ui.artifacts_view import ArtifactsViewWidget    # ← Phase 9F: Artifacts
from app.ui.events_view import EventsViewWidget          # ← Phase 9G: Events
from app.ui.stories_view import StoriesViewWidget        # ← Phase 9H: Stories
from app.ui.search_view import SearchViewWidget          # ← Search
from app.ui.lore_upload_view import LoreUploadViewWidget # ← Lore Upload
from app.ui.analytics_view import AnalyticsViewWidget    # ← Analytics
from app.ui.settings_view import SettingsViewWidget      # ← Settings
from app.ui.story_writer_view import StoryWriterViewWidget  # ← Module 11
from app.ui.cosmic_view import CosmicViewWidget          # ← Module 9: Cosmic View
from app.ui.simulation_view import SimulationViewWidget  # ← Module 12: World Simulation


class ZenMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zen AI — Zendrix Multiverse OS")
        self.resize(1280, 800)
        self.setStyleSheet("background-color: #0D0D0D; color: #FFFFFF;")

        # Window icon
        if _LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(_LOGO_PATH)))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ────────────────────────────────────
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setStyleSheet(
            "background-color: #111111; border-right: 1px solid #1E1E1E;"
        )
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 28, 12, 28)
        sidebar_layout.setSpacing(4)

        # ── Logo image at top of sidebar ──
        if _LOGO_PATH.exists():
            logo_lbl = QLabel()
            pixmap = QPixmap(str(_LOGO_PATH))
            # Scale to sidebar width, keep aspect ratio
            scaled = pixmap.scaledToWidth(196, Qt.SmoothTransformation)
            logo_lbl.setPixmap(scaled)
            logo_lbl.setAlignment(Qt.AlignCenter)
            logo_lbl.setStyleSheet(
                "border: none; border-radius: 10px; "
                "margin: 0 4px 0 4px;"
            )
            logo_lbl.setFixedHeight(scaled.height())
            sidebar_layout.addWidget(logo_lbl)
            sidebar_layout.addSpacing(8)

        # ZEN AI text below the image
        title_label = QLabel("ZEN AI")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: 900; color: #00ADB5; "
            "border: none; letter-spacing: 4px;"
        )
        title_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title_label)

        sub_label = QLabel("Zendrix Multiverse OS")
        sub_label.setStyleSheet(
            "font-size: 9px; color: #2A2A2A; border: none; letter-spacing: 1px;"
        )
        sub_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(sub_label)
        sidebar_layout.addSpacing(20)

        # ── Page definitions ──────────────────────────
        # (name, icon, widget_factory or None for placeholder)
        self._pages = [
            ("Dashboard",         "◈", DashboardWidget),
            ("Universes",         "🌐", UniversesViewWidget),
            ("Root Entities",     "★", RootEntitiesViewWidget),
            ("Characters",        "👤", CharactersViewWidget),
            ("Factions",          "⚔", FactionsViewWidget),
            ("Locations",         "📍", LocationsViewWidget),
            ("Artifacts",         "💎", ArtifactsViewWidget),
            ("Events",            "📅", EventsViewWidget),
            ("Stories",           "📖", StoriesViewWidget),
            ("─────────────", "",  None),          # divider
            ("Lore Graph",        "⬡", GraphViewWidget),
            ("Cosmic View",      "✴", CosmicViewWidget),
            ("Timeline",          "⏱", TimelineViewWidget),
            ("─────────────", "",  None),          # divider
            ("Wiki",              "📚", WikiViewWidget),
            ("AI Assistant",      "❆", AIChatWidget),
            ("AI Story Writer",  "📕", StoryWriterViewWidget),
            ("─────────────", "",  None),          # divider
            ("Search",            "🔍", SearchViewWidget),
            ("Lore Upload",       "⬆", LoreUploadViewWidget),
            ("Analytics",        "📊", AnalyticsViewWidget),
            ("Simulation",       "🌐", SimulationViewWidget),
            ("Settings",          "⚙", SettingsViewWidget),
        ]

        # ── Content Area ──────────────────────────────
        self.content_area = QStackedWidget()
        self.nav_buttons = {}
        self._page_index = 0   # tracks real stacked-widget index (skips dividers)

        # Section group labels
        def section_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(
                "color: #2A2A2A; font-size: 10px; font-weight: 700; "
                "letter-spacing: 2px; padding: 12px 8px 4px 8px; border: none;"
            )
            return lbl

        stack_idx = 0   # real QStackedWidget index
        for page_name, icon, factory in self._pages:
            # ── Divider / section label ──
            if page_name.startswith("──"):
                sidebar_layout.addSpacing(6)
                continue

            # ── Nav button ──
            btn = QPushButton(f"  {icon}  {page_name}")
            btn.setStyleSheet(self._btn_style())
            btn.setCheckable(True)
            btn.setFixedHeight(38)
            btn.clicked.connect(
                lambda checked, idx=stack_idx: self.switch_page(idx)
            )
            sidebar_layout.addWidget(btn)
            self.nav_buttons[stack_idx] = btn

            # ── Page widget ──
            if factory is not None:
                widget = factory()
            else:
                widget = self._placeholder(page_name)
            self.content_area.addWidget(widget)

            stack_idx += 1

        sidebar_layout.addStretch()

        # Version tag at bottom
        ver_lbl = QLabel("v1.3")
        ver_lbl.setStyleSheet("color: #222; font-size: 10px; border: none;")
        ver_lbl.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(ver_lbl)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_area)

        # Open dashboard by default
        self.switch_page(0)

    # ── Helpers ──────────────────────────────────────

    def _placeholder(self, name: str) -> QLabel:
        lbl = QLabel(f"{name}\n\nUnder Construction")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            "color: #222222; font-size: 18px; font-weight: 600; "
            "background: #0D0D0D;"
        )
        return lbl

    def _btn_style(self) -> str:
        return """
            QPushButton {
                background-color: transparent;
                color: #555555;
                text-align: left;
                padding: 0 10px;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1A1A1A;
                color: #CCCCCC;
            }
            QPushButton:checked {
                background-color: #002B2E;
                color: #00ADB5;
                border-left: 2px solid #00ADB5;
            }
        """

    def switch_page(self, index: int):
        self.content_area.setCurrentIndex(index)
        for i, btn in self.nav_buttons.items():
            btn.setChecked(i == index)
