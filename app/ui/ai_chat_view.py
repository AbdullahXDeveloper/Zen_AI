
# from PySide6.QtWidgets import (
#     QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, 
#     QLineEdit, QPushButton, QLabel
# )
# from PySide6.QtCore import QThread, Signal, Qt
# from PySide6.QtGui import QTextCursor  # <-- Yeh naya import add kiya hai
# from app.ai.claude_client import get_client

# # Background Thread AI ke liye
# class AIWorker(QThread):
#     response_ready = Signal(str)
#     error_occurred = Signal(str)

#     def __init__(self, prompt):
#         super().__init__()
#         self.prompt = prompt

#     def run(self):
#         try:
#             ai = get_client()
#             reply = ai.ask(self.prompt, system_prompt="You are Zen, the AI assistant for the Zendrix Multiverse.")
#             self.response_ready.emit(reply)
#         except Exception as e:
#             self.error_occurred.emit(str(e))


# class AIChatWidget(QWidget):
#     def __init__(self):
#         super().__init__()
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(20, 20, 20, 20)
#         layout.setSpacing(15)

#         # Header
#         header = QLabel("🧠 Zen AI Assistant (Local Offline Mode)")
#         header.setStyleSheet("font-size: 22px; font-weight: bold; color: #00ADB5;")
#         layout.addWidget(header)

#         # Chat History Box
#         self.chat_history = QTextBrowser()
#         self.chat_history.setStyleSheet("""
#             QTextBrowser {
#                 background-color: #1A1A1A;
#                 border: 1px solid #333;
#                 border-radius: 8px;
#                 padding: 15px;
#                 font-size: 15px;
#                 line-height: 1.5;
#                 color: #E0E0E0;
#             }
#         """)
#         layout.addWidget(self.chat_history)

#         # Input Area Layout
#         input_layout = QHBoxLayout()
        
#         self.input_field = QLineEdit()
#         self.input_field.setPlaceholderText("Ask Zen about your multiverse, or generate new lore...")
#         self.input_field.setStyleSheet("""
#             QLineEdit {
#                 background-color: #2D2D2D;
#                 border: 1px solid #444;
#                 border-radius: 6px;
#                 padding: 12px;
#                 font-size: 15px;
#                 color: #FFF;
#             }
#             QLineEdit:focus { border: 1px solid #00ADB5; }
#         """)
#         self.input_field.returnPressed.connect(self.send_message)
        
#         self.send_btn = QPushButton("Send")
#         self.send_btn.setStyleSheet("""
#             QPushButton {
#                 background-color: #00ADB5;
#                 color: #121212;
#                 font-weight: bold;
#                 border: none;
#                 border-radius: 6px;
#                 padding: 12px 20px;
#                 font-size: 15px;
#             }
#             QPushButton:hover { background-color: #008C9E; }
#             QPushButton:disabled { background-color: #555; color: #888; }
#         """)
#         self.send_btn.clicked.connect(self.send_message)

#         input_layout.addWidget(self.input_field)
#         input_layout.addWidget(self.send_btn)
        
#         layout.addLayout(input_layout)

#     def send_message(self):
#         user_text = self.input_field.text().strip()
#         if not user_text: return

#         self.append_message("You", user_text, "#FFFFFF")
#         self.input_field.clear()
        
#         self.send_btn.setDisabled(True)
#         self.input_field.setDisabled(True)
#         self.append_message("Zen", "Thinking...", "#888888")

#         self.worker = AIWorker(user_text)
#         self.worker.response_ready.connect(self.handle_response)
#         self.worker.error_occurred.connect(self.handle_error)
#         self.worker.start()

#     def handle_response(self, text):
#         # Yahan bug tha jo ab theek ho gaya hai (QTextCursor add kiya hai)
#         cursor = self.chat_history.textCursor()
#         cursor.movePosition(QTextCursor.End)
#         cursor.select(QTextCursor.BlockUnderCursor)
#         cursor.removeSelectedText()
#         cursor.deletePreviousChar() 

#         self.append_message("Zen", text, "#00ADB5")
#         self.reset_inputs()

#     def handle_error(self, error):
#         self.append_message("System Error", error, "#FF4C4C")
#         self.reset_inputs()

#     def reset_inputs(self):
#         self.send_btn.setDisabled(False)
#         self.input_field.setDisabled(False)
#         self.input_field.setFocus()

#     def append_message(self, sender, text, color):
#         html = f"<b><span style='color:{color}'>{sender}:</span></b> {text}<br><br>"
#         self.chat_history.append(html)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, 
    QLineEdit, QPushButton, QLabel, QComboBox
)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QTextCursor
from app.ai.claude_client import get_client

class AIWorker(QThread):
    response_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, prompt, provider):
        super().__init__()
        self.prompt = prompt
        self.provider = provider

    def run(self):
        try:
            ai = get_client(self.provider)
            reply = ai.ask(self.prompt, system_prompt="You are Zen, the AI assistant for the Zendrix Multiverse.")
            self.response_ready.emit(reply)
        except Exception as e:
            self.error_occurred.emit(str(e))


class AIChatWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header row with provider switch
        header_row = QHBoxLayout()
        header = QLabel("🧠 Zen AI Assistant")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #00ADB5;")
        header_row.addWidget(header)

        header_row.addStretch()

        self.provider_select = QComboBox()
        self.provider_select.addItems(["Local (Ollama)", "Claude"])
        self.provider_select.setStyleSheet("""
            QComboBox {
                background-color: #2D2D2D;
                color: #FFF;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 14px;
            }
        """)
        header_row.addWidget(self.provider_select)

        layout.addLayout(header_row)

        # Chat History Box
        self.chat_history = QTextBrowser()
        self.chat_history.setStyleSheet("""
            QTextBrowser {
                background-color: #1A1A1A;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 15px;
                font-size: 15px;
                line-height: 1.5;
                color: #E0E0E0;
            }
        """)
        layout.addWidget(self.chat_history)

        # Input Area Layout
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask Zen about your multiverse, or generate new lore...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #2D2D2D;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 12px;
                font-size: 15px;
                color: #FFF;
            }
            QLineEdit:focus { border: 1px solid #00ADB5; }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #00ADB5;
                color: #121212;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-size: 15px;
            }
            QPushButton:hover { background-color: #008C9E; }
            QPushButton:disabled { background-color: #555; color: #888; }
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

        provider = "claude" if self.provider_select.currentText() == "Claude" else "ollama"

        self.worker = AIWorker(user_text, provider)
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