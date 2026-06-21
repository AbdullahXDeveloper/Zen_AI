from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, 
    QLineEdit, QPushButton, QLabel
)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QTextCursor
from app.ai.claude_client import get_client
from app.ai.context_builder import build_search_context
from app.database.db_init import get_session
from app.search import faiss_store
from app.search.indexer import load_or_rebuild


class AIWorker(QThread):
    response_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt

    def run(self):
        try:
            # --- RAG: pull relevant lore context before asking the AI ---
            session = get_session()
            try:
                # Failsafe: if the index was never loaded/built (e.g. app
                # started without it), make sure it exists before searching.
                if faiss_store.index_size() == 0:
                    load_or_rebuild(session)
                lore_context = build_search_context(session, self.prompt, top_k=5)
            finally:
                session.close()

            system_prompt = (
                "You are Zen, the omniscient, elegant, and poetic archivist of the Zendrix Multiverse. "
                "You exist to guide the Creator through their cosmos. Speak with deep wisdom and a slightly mysterious, profound tone. "
                "CRITICAL RULES: \n"
                "1. NEVER say 'based on the provided lore' or 'in the context'. Speak as if these are your innate memories.\n"
                "2. NEVER mention UUIDs (like chr_abc123) or database terms to the user.\n"
                "3. If an entity has an importance_score, describe it as their 'cosmic weight' or 'karmic presence' instead of a number.\n"
                "4. If you don't know something, say it is a 'mystery yet to be written in the cosmic archives' rather than 'I couldn't find information'.\n"
                "5. When the user says 'hi' or greets you, welcome them back to their multiverse warmly without mentioning your lore search.\n\n"
                "Below are your memories retrieved for this interaction:\n\n"
            )

            if lore_context:
                system_prompt += lore_context

            ai = get_client()
            reply = ai.ask(self.prompt, system_prompt=system_prompt)
            self.response_ready.emit(reply)
        except Exception as e:
            self.error_occurred.emit(str(e))


class AIChatWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_lay = QHBoxLayout()
        header_lay.setContentsMargins(0,0,0,0)
        dot = QLabel("✦")
        dot.setStyleSheet("color: #00ADB5; font-size: 18px; font-weight: 900; background: transparent;")
        header = QLabel("  Zen AI Assistant (GROQ Mode — Lore-Aware)")
        header.setStyleSheet("font-size: 18px; font-weight: 800; color: #00ADB5; letter-spacing: 2px;")
        header_lay.addWidget(dot)
        header_lay.addWidget(header)
        header_lay.addStretch()
        layout.addLayout(header_lay)

        # Chat History Box
        self.chat_history = QTextBrowser()
        self.chat_history.setStyleSheet("""
            QTextBrowser {
                background-color: #121212;
                border: 1px solid #262626;
                border-radius: 12px;
                padding: 20px;
                font-size: 14px;
                line-height: 1.6;
                color: #EEEEEE;
            }
            QScrollBar:vertical {
                background: #111; width: 8px; border-radius: 4px; margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #333; border-radius: 4px; min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #00ADB5; }
        """)
        layout.addWidget(self.chat_history)

        # Input Area Layout
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(" Ask Zen about your multiverse, or generate new lore...")
        self.input_field.setFixedHeight(48)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(20, 20, 20, 0.9);
                border: 1px solid #333;
                border-radius: 12px;
                padding: 0 16px;
                font-size: 14px;
                color: #FFF;
            }
            QLineEdit:focus { border: 1px solid #00ADB5; background-color: #1A1A1A; }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        
        self.send_btn = QPushButton("✦  Send")
        self.send_btn.setFixedHeight(48)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00ADB5, stop:1 #008C9E);
                color: #111111;
                font-weight: 800;
                letter-spacing: 1px;
                border: none;
                border-radius: 12px;
                padding: 0 24px;
                font-size: 14px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d2dc, stop:1 #00a4b8); }
            QPushButton:disabled { background: #333; color: #666; }
        """)
        self.send_btn.clicked.connect(self.send_message)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        
        layout.addLayout(input_layout)

    def send_message(self):
        user_text = self.input_field.text().strip()
        if not user_text: return

        self.append_message("You", user_text, "#FFFFFF")
        self.input_field.clear()
        
        self.send_btn.setDisabled(True)
        self.input_field.setDisabled(True)
        self.append_message("Zen", "Thinking...", "#888888")

        self.worker = AIWorker(user_text)
        self.worker.response_ready.connect(self.handle_response)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.start()

    def handle_response(self, text):
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar() 

        self.append_message("Zen", text, "#00ADB5")
        self.reset_inputs()

    def handle_error(self, error):
        self.append_message("System Error", error, "#FF4C4C")
        self.reset_inputs()

    def reset_inputs(self):
        self.send_btn.setDisabled(False)
        self.input_field.setDisabled(False)
        self.input_field.setFocus()

    def append_message(self, sender, text, color):
        html = f"<b><span style='color:{color}'>{sender}:</span></b> {text}<br><br>"
        self.chat_history.append(html)