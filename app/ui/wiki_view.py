import os
from PySide6.QtWidgets import QWidget, QHBoxLayout, QListWidget, QTextBrowser

class WikiViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Left Side: List of Wiki Pages
        self.file_list = QListWidget()
        self.file_list.setFixedWidth(250)
        self.file_list.setStyleSheet("""
            QListWidget {
                background-color: #1A1A1A;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 5px;
                outline: none;
            }
            QListWidget::item { padding: 10px; border-radius: 5px; color: #D3D3D3; }
            QListWidget::item:hover { background-color: #2D2D2D; color: white; }
            QListWidget::item:selected { background-color: #00ADB5; color: white; font-weight: bold; }
        """)
        self.file_list.currentTextChanged.connect(self.load_wiki)
        
        # Right Side: Markdown Renderer
        self.text_display = QTextBrowser()
        self.text_display.setOpenExternalLinks(True)
        self.text_display.setStyleSheet("""
            QTextBrowser {
                background-color: #1A1A1A;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 25px;
                font-size: 15px;
                line-height: 1.6;
                color: #E0E0E0;
            }
        """)
        
        layout.addWidget(self.file_list)
        layout.addWidget(self.text_display)
        self.load_files()
        
    def load_files(self):
        wiki_dir = os.path.join("data", "lore", "wiki")
        if not os.path.exists(wiki_dir): 
            return
            
        for root, dirs, files in os.walk(wiki_dir):
            for f in files:
                if f.endswith(".md"):
                    self.file_list.addItem(f.replace(".md", ""))
                    
    def load_wiki(self, item_name):
        if not item_name: return
        wiki_dir = os.path.join("data", "lore", "wiki")
        for root, dirs, files in os.walk(wiki_dir):
            for f in files:
                if f == f"{item_name}.md":
                    with open(os.path.join(root, f), "r", encoding="utf-8") as file:
                        self.text_display.setMarkdown(file.read())
                    return