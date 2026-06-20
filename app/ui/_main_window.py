
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QStackedWidget, QLabel, QFrame
)
from PySide6.QtCore import Qt
from app.ui.wiki_view import WikiViewWidget
from app.ui.ai_chat_view import AIChatWidget  # <-- Naya AI Chat Widget Import

class ZenMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zen AI - Zendrix Multiverse OS")
        self.resize(1280, 800)
        self.setStyleSheet("background-color: #0D0D0D; color: #FFFFFF;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar Setup
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(260)
        self.sidebar.setStyleSheet("background-color: #151515; border-right: 1px solid #222;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 30, 15, 30)
        sidebar_layout.setSpacing(8)

        # App Title
        title_label = QLabel("ZEN AI")
        title_label.setStyleSheet("font-size: 26px; font-weight: 900; color: #00ADB5; border: none; letter-spacing: 3px;")
        title_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title_label)
        sidebar_layout.addSpacing(40)

        # 2. Main Content Area
        self.content_area = QStackedWidget()
        
        # Setup Pages
        self.nav_buttons = {}
        pages = [
            "Dashboard", "Universes", "Characters", "Factions", 
            "Lore Graph", "Timeline", "Wiki View", "AI Story Assistant"
        ]
        
        for i, page_name in enumerate(pages):
            btn = QPushButton(page_name)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #888888;
                    text-align: left;
                    padding: 14px 18px;
                    border: none;
                    border-radius: 6px;
                    font-weight: 600;
                }
                QPushButton:hover { background-color: #1E1E1E; color: #E0E0E0; }
                QPushButton:checked { background-color: #00ADB5; color: #FFFFFF; }
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, index=i: self.switch_page(index))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[i] = btn
            
            # ---> YAHAN WOH CODE ADD HUA HAI <---
            
            # Agar index 6 (Wiki View) hai
            if i == 6:
                self.content_area.addWidget(WikiViewWidget())
            # Agar index 7 (AI Story Assistant) hai
            elif i == 7:
                self.content_area.addWidget(AIChatWidget())
            # Baqi sab ke liye dummy page
            else:
                dummy_page = QLabel(f"{page_name} Module - Under Construction")
                dummy_page.setAlignment(Qt.AlignCenter)
                dummy_page.setStyleSheet("font-size: 20px; color: #444;")
                self.content_area.addWidget(dummy_page)

        sidebar_layout.addStretch()

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_area)

        # Default dashboard open rakhein
        self.switch_page(0)

    def switch_page(self, index):
        self.content_area.setCurrentIndex(index)
        for i, btn in self.nav_buttons.items():
            btn.setChecked(i == index)