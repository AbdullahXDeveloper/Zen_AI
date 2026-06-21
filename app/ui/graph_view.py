"""
app/ui/graph_view.py
Module 8b — Knowledge Graph View
Renders PyVis HTML graphs inside PySide6 using QWebEngineView.
"""

import os
import tempfile
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QFrame, QSizePolicy, QSpinBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QUrl, QThread, Signal

from app.database.db_init import get_session
from app.graph.engine import (
    build_multiverse_graph,
    build_universe_graph,
    build_character_graph,
    build_root_entity_graph,
    export_graph_to_html
)
from app.database.models import Universe, Character, RootEntity


# ─────────────────────────────────────────────
# Background thread: graph build karo, freeze mat karo UI
# ─────────────────────────────────────────────
class GraphWorker(QThread):
    graph_ready = Signal(str)   # HTML file path emit karta hai
    error = Signal(str)

    def __init__(self, graph_type, entity_id=None):
        super().__init__()
        self.graph_type = graph_type
        self.entity_id = entity_id

    def run(self):
        try:
            session = get_session()
            if self.graph_type == "multiverse":
                G = build_multiverse_graph(session)
            elif self.graph_type == "universe":
                G = build_universe_graph(session, self.entity_id)
            elif self.graph_type == "character":
                G = build_character_graph(session, self.entity_id)
            elif self.graph_type == "root_entity":
                G = build_root_entity_graph(session, self.entity_id)
            else:
                self.error.emit(f"Unknown graph type: {self.graph_type}")
                return

            # Temp file mein save karo
            tmp = tempfile.NamedTemporaryFile(
                suffix=".html", delete=False, prefix="zenai_graph_"
            )
            export_graph_to_html(G, tmp.name)
            self.graph_ready.emit(tmp.name)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


# ─────────────────────────────────────────────
# Main Graph View Widget
# ─────────────────────────────────────────────
class GraphViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._worker = None
        self._last_tmp_path = None   # tracks last temp HTML file for cleanup
        self._setup_ui()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Top Control Bar ──
        control_bar = QFrame()
        control_bar.setFixedHeight(70)
        control_bar.setStyleSheet("""
            QFrame {
                background-color: rgba(20, 20, 20, 0.9);
                border-bottom: 1px solid #333333;
                border-bottom-left-radius: 15px;
                border-bottom-right-radius: 15px;
            }
        """)
        bar_layout = QHBoxLayout(control_bar)
        bar_layout.setContentsMargins(25, 0, 25, 0)
        bar_layout.setSpacing(15)

        # Graph type dropdown
        type_label = QLabel("Graph:")
        type_label.setStyleSheet("color: #888888; font-size: 13px;")
        self.graph_type_combo = QComboBox()
        self.graph_type_combo.addItems([
            "Multiverse Overview",
            "Universe Graph",
            "Character Graph",
            "Root Entity Graph",
        ])
        self.graph_type_combo.setStyleSheet(_combo_style())
        self.graph_type_combo.currentIndexChanged.connect(self._on_type_changed)

        # Entity ID selector (sirf jab zaroori ho)
        self.entity_label = QLabel("Entity ID:")
        self.entity_label.setStyleSheet("color: #888888; font-size: 13px;")
        self.entity_combo = QComboBox()
        self.entity_combo.setMinimumWidth(200)
        self.entity_combo.setStyleSheet(_combo_style())
        self.entity_frame = QFrame()
        ef_layout = QHBoxLayout(self.entity_frame)
        ef_layout.setContentsMargins(0, 0, 0, 0)
        ef_layout.setSpacing(8)
        ef_layout.addWidget(self.entity_label)
        ef_layout.addWidget(self.entity_combo)
        self.entity_frame.hide()

        # Generate button
        self.generate_btn = QPushButton("✦  Generate Graph")
        self.generate_btn.setFixedHeight(40)
        self.generate_btn.setStyleSheet(_btn_style())
        self.generate_btn.clicked.connect(self._generate_graph)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #00ADB5; font-size: 13px; font-weight: 700;")

        bar_layout.addWidget(type_label)
        bar_layout.addWidget(self.graph_type_combo)
        bar_layout.addWidget(self.entity_frame)
        bar_layout.addStretch()
        bar_layout.addWidget(self.status_label)
        bar_layout.addWidget(self.generate_btn)

        # ── WebEngine View ──
        self.web_view = QWebEngineView()
        self.web_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.web_view.setStyleSheet("background: #1E1E1E;")
        self._show_placeholder()

        root_layout.addWidget(control_bar)
        root_layout.addWidget(self.web_view)

        # Init entity combo for default type
        self._on_type_changed(0)

    # ── Helpers ──────────────────────────────

    def _show_placeholder(self):
        placeholder_html = """
        <html><body style="background:#1E1E1E; color:#333; 
            display:flex; align-items:center; justify-content:center; 
            height:100vh; margin:0; font-family:sans-serif;">
          <div style="text-align:center;">
            <div style="font-size:64px; opacity:0.15;">⬡</div>
            <p style="font-size:16px; margin-top:16px; color:#444;">
              Graph type choose karein aur Generate dabayein
            </p>
          </div>
        </body></html>
        """
        self.web_view.setHtml(placeholder_html)

    def _show_loading(self):
        loading_html = """
        <html><body style="background:#1E1E1E; color:#555; 
            display:flex; align-items:center; justify-content:center; 
            height:100vh; margin:0; font-family:sans-serif;">
          <div style="text-align:center;">
            <div style="font-size:48px; animation:spin 1s linear infinite;">⬡</div>
            <p style="font-size:15px; margin-top:20px; color:#00ADB5;">
              Graph build ho raha hai...
            </p>
          </div>
        </body></html>
        """
        self.web_view.setHtml(loading_html)

    def _populate_entity_combo(self, entity_type):
        """DB se entities fetch karke combo populate karo."""
        self.entity_combo.clear()
        session = None
        try:
            session = get_session()
            if entity_type == "universe":
                items = session.query(Universe).order_by(Universe.name).all()
                for item in items:
                    self.entity_combo.addItem(f"{item.name} (ID: {item.id})", item.id)
            elif entity_type == "character":
                items = session.query(Character).order_by(Character.name).all()
                for item in items:
                    self.entity_combo.addItem(f"{item.name} (ID: {item.id})", item.id)
            elif entity_type == "root_entity":
                items = session.query(RootEntity).order_by(RootEntity.name).all()
                for item in items:
                    self.entity_combo.addItem(f"{item.name} (ID: {item.id})", item.id)
        except Exception as e:
            self.entity_combo.addItem(f"Error: {e}")
        finally:
            if session:
                session.close()

    # ── Slots ─────────────────────────────────

    def _on_type_changed(self, index):
        type_map = {
            0: "multiverse",
            1: "universe",
            2: "character",
            3: "root_entity",
        }
        gtype = type_map.get(index, "multiverse")
        needs_entity = gtype in ("universe", "character", "root_entity")
        self.entity_frame.setVisible(needs_entity)

        label_map = {
            "universe": "Universe:",
            "character": "Character:",
            "root_entity": "Root Entity:",
        }
        if needs_entity:
            self.entity_label.setText(label_map.get(gtype, "Entity:"))
            self._populate_entity_combo(gtype)

    def _generate_graph(self):
        type_map = {
            0: "multiverse",
            1: "universe",
            2: "character",
            3: "root_entity",
        }
        idx = self.graph_type_combo.currentIndex()
        gtype = type_map.get(idx, "multiverse")

        entity_id = None
        if gtype != "multiverse":
            entity_id = self.entity_combo.currentData()
            if entity_id is None:
                self.status_label.setText("⚠ Pehle entity choose karein")
                return

        self.generate_btn.setEnabled(False)
        self.status_label.setText("Building...")
        self._show_loading()

        self._worker = GraphWorker(gtype, entity_id)
        self._worker.graph_ready.connect(self._on_graph_ready)
        self._worker.error.connect(self._on_graph_error)
        self._worker.start()


    def _on_graph_ready(self, html_path):
        import os, re, tempfile

        vis_cache = os.path.join("data", "cache", "vis-network.min.js")

        if not os.path.exists(vis_cache):
            import urllib.request
            os.makedirs(os.path.dirname(vis_cache), exist_ok=True)
            urllib.request.urlretrieve(
                "https://cdn.jsdelivr.net/npm/vis-network@9.1.2/dist/vis-network.min.js",
                vis_cache
            )

        with open(vis_cache, 'r', encoding='utf-8') as f:
            vis_js = f.read()

        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()

        # CDN script tag ko locally cached vis.js se replace karo
        match = re.search(r'<script[^>]+src=["\']([^"\']*vis[^"\']*)["\'][^>]*></script>', html)
        if match:
            old_tag = match.group(0)
            html = html.replace(old_tag, f'<script type="text/javascript">{vis_js}</script>')

        # Height fix
        html = html.replace('height: 800px', 'height: 100vh')

        # Force dark background — prevents random white flash on every load
        dark_css = (
            "<style>"
            "html, body { background-color: #1E1E1E !important; margin: 0; padding: 0; }"
            "#mynetwork { background-color: #1E1E1E !important; }"
            "</style>"
        )
        html = html.replace("</head>", dark_css + "\n</head>", 1)

        # ── KEY FIX ──────────────────────────────────────────────────────────
        # setHtml() ka ek hidden 2 MB content limit hai.  Jab vis.js inline
        # ho jata hai (~600 KB) + graph HTML milake limit cross ho sakti hai
        # — result: silent blank/white page.
        # Fix: HTML ko disk par ek real temp file mein likhein, phir
        # load(QUrl.fromLocalFile(...)) se load karein.  WebEngine file ko
        # direct disk se padhta hai, koi size limit nahi.
        # ─────────────────────────────────────────────────────────────────────
        final_tmp = tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, prefix="zenai_final_",
            mode='w', encoding='utf-8'
        )
        final_tmp.write(html)
        final_tmp.close()

        # Purana temp file clean up karo (memory leak avoid)
        if hasattr(self, '_last_tmp_path') and self._last_tmp_path:
            try:
                os.unlink(self._last_tmp_path)
            except Exception:
                pass
        self._last_tmp_path = final_tmp.name

        self.web_view.load(QUrl.fromLocalFile(final_tmp.name))

        self.status_label.setText("✓ Graph ready")
        self.generate_btn.setEnabled(True)

    def _on_graph_error(self, msg):
        self.status_label.setText(f"Error: {msg}")
        self.generate_btn.setEnabled(True)
        error_html = f"""
        <html><body style="background:#1E1E1E; color:#e74c3c; 
            display:flex; align-items:center; justify-content:center; 
            height:100vh; margin:0; font-family:sans-serif;">
          <div style="text-align:center; max-width:500px;">
            <div style="font-size:40px;">⚠</div>
            <p style="margin-top:16px; font-size:14px;">{msg}</p>
          </div>
        </body></html>
        """
        self.web_view.setHtml(error_html)


# ─────────────────────────────────────────────
# Style helpers
# ─────────────────────────────────────────────
def _combo_style():
    return """
        QComboBox {
            background-color: #121212;
            color: #EEEEEE;
            border: 1px solid #2A2A2A;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 14px;
            min-width: 180px;
        }
        QComboBox:hover { border-color: #00ADB5; background-color: #1A1A1A; }
        QComboBox QAbstractItemView {
            background-color: #1A1A1A;
            color: #CCCCCC;
            selection-background-color: #00ADB5;
            border-radius: 8px;
        }
    """

def _btn_style():
    return """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00ADB5, stop:1 #008C9E);
            color: #111111;
            font-weight: 800;
            letter-spacing: 1px;
            border: none;
            border-radius: 10px;
            padding: 0 24px;
            font-size: 14px;
        }
        QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d2dc, stop:1 #00a4b8); }
        QPushButton:disabled { background: #333; color: #666; }
    """
