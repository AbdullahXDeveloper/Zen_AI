"""
app/ui/graph_view.py
Module 8b — Knowledge Graph View (Rewritten)

A premium interactive knowledge graph with:
- Directed edges (DiGraph)
- Node inspector side panel
- Color-coded legend
- Search / node highlight
- Layout selector (Force / Hierarchical / Circular)
- Manual edge editor (add & delete)
- Export to HTML
- Fully offline (vis.js cached locally)
"""

import os
import tempfile
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QFrame, QSizePolicy, QMessageBox, QInputDialog,
    QSplitter, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QScrollArea, QFileDialog, QApplication
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtCore import Qt, QUrl, QThread, Signal, QTimer

from app.database.db_init import get_session
from app.graph.engine import (
    build_multiverse_graph,
    build_universe_graph,
    build_character_graph,
    build_root_entity_graph,
    export_graph_to_html,
    GROUP_STYLES,
)
from app.database.models import Universe, Character, RootEntity
from app.graph.bridge import GraphBridge


# ──────────────────────────────────────────────────────────────────────────────
# Background worker: builds graph off-thread so UI doesn't freeze
# ──────────────────────────────────────────────────────────────────────────────
class GraphWorker(QThread):
    graph_ready = Signal(str, object)   # (html_path, nx_graph)
    error = Signal(str)

    def __init__(self, graph_type: str, entity_id=None):
        super().__init__()
        self.graph_type = graph_type
        self.entity_id = entity_id

    def run(self):
        session = None
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

            tmp = tempfile.NamedTemporaryFile(
                suffix=".html", delete=False, prefix="zenai_graph_"
            )
            tmp.close()
            export_graph_to_html(G, tmp.name)
            self.graph_ready.emit(tmp.name, G)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if session:
                session.close()


# ──────────────────────────────────────────────────────────────────────────────
# Custom WebEnginePage — intercepts console.log bridge messages
# ──────────────────────────────────────────────────────────────────────────────
class CustomWebEnginePage(QWebEnginePage):
    node_clicked = Signal(str, str, str)   # node_id, label, group

    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.bridge: GraphBridge | None = None

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        if message.startswith("ZEN_NODE_CLICK:"):
            parts = message.split(":", 4)
            # ZEN_NODE_CLICK:node_id:label:group
            if len(parts) >= 4:
                self.node_clicked.emit(parts[1], parts[2], parts[3] if len(parts) > 3 else "")

        elif message.startswith("ZEN_BRIDGE:"):
            parts = message.split(":", 5)
            # ZEN_BRIDGE:CMD:from:to:label
            if len(parts) >= 4 and self.bridge:
                cmd = parts[1]
                from_id = parts[2]
                to_id = parts[3]
                label = parts[4] if len(parts) > 4 else ""
                if cmd == "ADD_EDGE":
                    self.bridge.add_edge(from_id, to_id, label)
                elif cmd == "DEL_EDGE":
                    self.bridge.delete_edge_by_nodes(from_id, to_id)

    def javaScriptAlert(self, securityOrigin, msg):
        QMessageBox.information(self.view(), "Graph", msg)

    def javaScriptConfirm(self, securityOrigin, msg):
        res = QMessageBox.question(self.view(), "Confirm", msg,
                                   QMessageBox.Yes | QMessageBox.No)
        return res == QMessageBox.Yes

    def javaScriptPrompt(self, securityOrigin, msg, defaultValue):
        text, ok = QInputDialog.getText(self.view(), "Input", msg, text=defaultValue)
        return (True, text) if ok else (False, "")


# ──────────────────────────────────────────────────────────────────────────────
# Main Graph View
# ──────────────────────────────────────────────────────────────────────────────
class GraphViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._worker: GraphWorker | None = None
        self._last_tmp_path: str | None = None
        self._current_nx_graph = None
        self._setup_ui()

    # ── UI Construction ────────────────────────────────────────────────────

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Control Bar ───────────────────────────────────────────────────
        control_bar = QFrame()
        control_bar.setFixedHeight(60)
        control_bar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #1a1a1a, stop:1 #111111);
                border-bottom: 1px solid #222222;
            }
        """)
        bar = QHBoxLayout(control_bar)
        bar.setContentsMargins(16, 0, 16, 0)
        bar.setSpacing(10)

        # Graph type selector
        self.graph_type_combo = QComboBox()
        self.graph_type_combo.addItems([
            "🌐  Multiverse Overview",
            "🌍  Universe Graph",
            "👤  Character Graph",
            "★  Root Entity Graph",
        ])
        self.graph_type_combo.setStyleSheet(_combo_style())
        self.graph_type_combo.setMinimumWidth(130)
        self.graph_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.graph_type_combo.currentIndexChanged.connect(self._on_type_changed)

        # Entity selector (shown when needed)
        self.entity_label = QLabel("Entity:")
        self.entity_label.setStyleSheet("color:#888; font-size:12px;")
        self.entity_combo = QComboBox()
        self.entity_combo.setMinimumWidth(100)
        self.entity_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.entity_combo.setStyleSheet(_combo_style())
        self.entity_frame = QFrame()
        ef = QHBoxLayout(self.entity_frame)
        ef.setContentsMargins(0, 0, 0, 0)
        ef.setSpacing(6)
        ef.addWidget(self.entity_label)
        ef.addWidget(self.entity_combo, stretch=1)
        self.entity_frame.hide()

        # Layout selector
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["⚛  Force Atlas", "🔀  Hierarchical", "⭕  Circular"])
        self.layout_combo.setStyleSheet(_combo_style())
        self.layout_combo.setMinimumWidth(110)
        self.layout_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.layout_combo.currentIndexChanged.connect(self._on_layout_changed)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍  Search nodes…")
        self.search_bar.setMaximumWidth(150)
        self.search_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background: #1a1a1a;
                color: #EEE;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #00ADB5; }
        """)
        self.search_bar.textChanged.connect(self._on_search_changed)
        self.search_bar.setEnabled(False)

        # Edit mode toggle
        self.edit_mode_btn = QPushButton("✎  Edit Mode")
        self.edit_mode_btn.setFixedHeight(36)
        self.edit_mode_btn.setStyleSheet(_btn_style())
        self.edit_mode_btn.setCheckable(True)
        self.edit_mode_btn.toggled.connect(self._toggle_edit_mode)
        self.edit_mode_btn.setEnabled(False)

        # Export button
        self.export_btn = QPushButton("⬇  Export")
        self.export_btn.setFixedHeight(36)
        self.export_btn.setStyleSheet(_btn_style_secondary())
        self.export_btn.clicked.connect(self._export_graph)
        self.export_btn.setEnabled(False)

        # Generate button
        self.generate_btn = QPushButton("✦  Generate")
        self.generate_btn.setFixedHeight(36)
        self.generate_btn.setStyleSheet(_btn_style())
        self.generate_btn.clicked.connect(self._generate_graph)

        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color:#00ADB5; font-size:12px; font-weight:700;")

        bar.addWidget(self.graph_type_combo)
        bar.addWidget(self.entity_frame)
        bar.addWidget(self.layout_combo)
        bar.addWidget(self.search_bar)
        bar.addStretch()
        bar.addWidget(self.status_label)
        bar.addWidget(self.edit_mode_btn)
        bar.addWidget(self.export_btn)
        bar.addWidget(self.generate_btn)

        # ── Main horizontal splitter: graph | right sidebar ──────────────────
        self.h_splitter = QSplitter(Qt.Horizontal)
        self.h_splitter.setChildrenCollapsible(False)

        # ── Graph web view (left, expands) ──────────────────────────────────
        self.web_view = QWebEngineView()
        self.page = CustomWebEnginePage(self.web_view.page().profile(), self.web_view)
        self.web_view.setPage(self.page)
        self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.web_view.setMinimumSize(0, 0)
        self.web_view.setStyleSheet("background: #141414;")

        self.bridge = GraphBridge()
        self.page.bridge = self.bridge
        self.page.node_clicked.connect(self._on_node_clicked)

        self._show_placeholder()
        self.h_splitter.addWidget(self.web_view)

        # ── Right sidebar ────────────────────────────────────────────────────
        self.sidebar = QWidget()
        self.sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.sidebar.setMinimumWidth(300)
        self.sidebar.setMaximumWidth(300)
        self.sidebar.setStyleSheet("background: #111111; border-left: 1px solid #222;")

        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        # ── Legend section ──────────────────────────────────────────────────
        legend_frame = QFrame()
        legend_frame.setStyleSheet("background: #0f0f0f; border-bottom: 1px solid #1e1e1e;")
        leg_layout = QVBoxLayout(legend_frame)
        leg_layout.setContentsMargins(14, 12, 14, 12)
        leg_layout.setSpacing(3)

        leg_title = QLabel("LEGEND")
        leg_title.setStyleSheet("color:#333; font-size:9px; font-weight:700; letter-spacing:3px;")
        leg_layout.addWidget(leg_title)
        leg_layout.addSpacing(4)

        legend_items = [
            ("Universe",    GROUP_STYLES["universe"]["color"]),
            ("Character",   GROUP_STYLES["character"]["color"]),
            ("Faction",     GROUP_STYLES["faction"]["color"]),
            ("Location",    GROUP_STYLES["location"]["color"]),
            ("Artifact",    GROUP_STYLES["artifact"]["color"]),
            ("Event",       GROUP_STYLES["event"]["color"]),
            ("Story",       GROUP_STYLES["story"]["color"]),
            ("Root Entity", GROUP_STYLES["root_entity"]["color"]),
        ]
        # Two-column legend grid
        leg_grid = QHBoxLayout()
        leg_grid.setSpacing(0)
        col_a, col_b = QVBoxLayout(), QVBoxLayout()
        col_a.setSpacing(2); col_b.setSpacing(2)
        for i, (name, color) in enumerate(legend_items):
            row = QHBoxLayout(); row.setSpacing(5)
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{color}; font-size:10px;")
            dot.setFixedWidth(14)
            lbl = QLabel(name)
            lbl.setStyleSheet("color:#666; font-size:11px;")
            row.addWidget(dot); row.addWidget(lbl); row.addStretch()
            (col_a if i < 4 else col_b).addLayout(row)
        leg_grid.addLayout(col_a); leg_grid.addLayout(col_b)
        leg_layout.addLayout(leg_grid)
        sb_layout.addWidget(legend_frame)

        # ── Node Inspector ──────────────────────────────────────────────────
        self.inspector_frame = QFrame()
        self.inspector_frame.setStyleSheet("background: #111; border-bottom: 1px solid #1e1e1e;")
        ins_layout = QVBoxLayout(self.inspector_frame)
        ins_layout.setContentsMargins(14, 12, 14, 12)
        ins_layout.setSpacing(4)

        QLabel("NODE INSPECTOR", styleSheet="color:#333; font-size:9px; font-weight:700; letter-spacing:3px;",
               parent=self.inspector_frame)
        ins_layout.addWidget(self.inspector_frame.findChildren(QLabel)[0])
        ins_layout.addSpacing(4)

        self.ins_name_lbl = QLabel("—")
        self.ins_name_lbl.setStyleSheet("color:#EEE; font-size:15px; font-weight:700;")
        self.ins_name_lbl.setWordWrap(True)
        ins_layout.addWidget(self.ins_name_lbl)

        self.ins_type_lbl = QLabel("")
        self.ins_type_lbl.setStyleSheet("font-size:10px; font-weight:700; padding:2px 8px; border-radius:8px;")
        ins_layout.addWidget(self.ins_type_lbl)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#1e1e1e; margin:4px 0;")
        ins_layout.addWidget(sep)

        self.ins_detail_lbl = QLabel("Click a node to inspect it.")
        self.ins_detail_lbl.setStyleSheet("color:#555; font-size:12px; line-height:1.5;")
        self.ins_detail_lbl.setWordWrap(True)
        self.ins_detail_lbl.setAlignment(Qt.AlignTop)
        ins_layout.addWidget(self.ins_detail_lbl)

        sb_layout.addWidget(self.inspector_frame)

        # ── Edge Editor (scrollable, fills remaining space) ─────────────────
        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        editor_scroll.setStyleSheet("""
            QScrollArea { border: none; background: #111; }
            QScrollBar:vertical { background: #0a0a0a; width: 5px; border-radius:2px; }
            QScrollBar::handle:vertical { background: #2a2a2a; border-radius: 2px; min-height:20px; }
            QScrollBar::handle:vertical:hover { background: #00ADB5; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """)

        editor_frame = QFrame()
        editor_frame.setStyleSheet("background: #111;")
        ed_layout = QVBoxLayout(editor_frame)
        ed_layout.setContentsMargins(14, 12, 14, 10)
        ed_layout.setSpacing(6)

        ed_hdr = QLabel("EDGE EDITOR")
        ed_hdr.setStyleSheet("color:#333; font-size:9px; font-weight:700; letter-spacing:3px;")
        ed_layout.addWidget(ed_hdr)
        ed_layout.addSpacing(4)

        # Source combo
        ed_layout.addWidget(QLabel("Source:", styleSheet="color:#555; font-size:11px;"))
        self.src_combo = QComboBox()
        self.src_combo.setPlaceholderText("Select source node")
        self.src_combo.setStyleSheet(_combo_style_compact())
        ed_layout.addWidget(self.src_combo)

        # Target combo
        ed_layout.addWidget(QLabel("Target:", styleSheet="color:#555; font-size:11px;"))
        self.tgt_combo = QComboBox()
        self.tgt_combo.setPlaceholderText("Select target node")
        self.tgt_combo.setStyleSheet(_combo_style_compact())
        ed_layout.addWidget(self.tgt_combo)

        # Label input
        ed_layout.addWidget(QLabel("Label:", styleSheet="color:#555; font-size:11px;"))
        self.lbl_input = QLineEdit()
        self.lbl_input.setPlaceholderText("e.g. Friend, Founded, Owns…")
        self.lbl_input.setStyleSheet(_input_style())
        ed_layout.addWidget(self.lbl_input)

        self.add_edge_btn = QPushButton("＋  Add Connection")
        self.add_edge_btn.setStyleSheet(_btn_style())
        self.add_edge_btn.setFixedHeight(34)
        self.add_edge_btn.clicked.connect(self._on_manual_add_edge)
        self.add_edge_btn.setEnabled(False)
        ed_layout.addWidget(self.add_edge_btn)

        ed_layout.addSpacing(8)
        ed_layout.addWidget(QLabel("Connections:", styleSheet="color:#555; font-size:11px;"))

        # Edge table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["From", "To  →  Label", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 34)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0D0D0D;
                color: #AAA;
                border: 1px solid #1a1a1a;
                border-radius: 6px;
                font-size: 11px;
                alternate-background-color: #111111;
            }
            QHeaderView::section {
                background: #0f0f0f;
                color: #444;
                font-size: 10px;
                font-weight: 700;
                border: none;
                padding: 5px 4px;
                border-bottom: 1px solid #1e1e1e;
            }
        """)
        ed_layout.addWidget(self.table)
        ed_layout.addStretch()

        editor_scroll.setWidget(editor_frame)
        sb_layout.addWidget(editor_scroll, stretch=1)

        self.h_splitter.addWidget(self.sidebar)

        # Lock splitter: graph grows, sidebar stays fixed
        self.h_splitter.setStretchFactor(0, 1)
        self.h_splitter.setStretchFactor(1, 0)
        self.h_splitter.setSizes([2000, 300])

        root_layout.addWidget(control_bar)
        root_layout.addWidget(self.h_splitter)

        # Init entity combo for default type
        self._on_type_changed(0)

    # ── Placeholder / Loading states ───────────────────────────────────────

    def _show_placeholder(self):
        self.web_view.setHtml(_placeholder_html())

    def _show_loading(self):
        self.web_view.setHtml(_loading_html())

    # ── Entity Combo ───────────────────────────────────────────────────────

    def _populate_entity_combo(self, entity_type: str):
        self.entity_combo.clear()
        session = None
        try:
            session = get_session()
            model_map = {
                "universe": Universe,
                "character": Character,
                "root_entity": RootEntity,
            }
            model = model_map.get(entity_type)
            if not model:
                return
            items = session.query(model).order_by(model.name).all()
            for item in items:
                self.entity_combo.addItem(f"{item.name}  (ID {item.id})", item.id)
        except Exception as e:
            self.entity_combo.addItem(f"Error: {e}")
        finally:
            if session:
                session.close()

    # ── Slots ──────────────────────────────────────────────────────────────

    def _on_type_changed(self, index: int):
        type_map = {0: "multiverse", 1: "universe", 2: "character", 3: "root_entity"}
        label_map = {"universe": "Universe:", "character": "Character:", "root_entity": "Root Entity:"}
        gtype = type_map.get(index, "multiverse")
        needs = gtype in ("universe", "character", "root_entity")
        self.entity_frame.setVisible(needs)
        if needs:
            self.entity_label.setText(label_map.get(gtype, "Entity:"))
            self._populate_entity_combo(gtype)

    def _on_layout_changed(self, index: int):
        modes = ["force", "hierarchical", "circular"]
        mode = modes[index] if index < len(modes) else "force"
        js = f"if (typeof window.zenSetLayout === 'function') {{ window.zenSetLayout('{mode}'); }}"
        self.web_view.page().runJavaScript(js)

    def _on_search_changed(self, text: str):
        escaped = text.replace("'", "\\'").replace("\\", "\\\\")
        js = f"if (typeof window.zenHighlight === 'function') {{ window.zenHighlight('{escaped}'); }}"
        self.web_view.page().runJavaScript(js)

    def _on_node_clicked(self, node_id: str, label: str, group: str):
        self.ins_name_lbl.setText(label or node_id)
        group_display = group.replace("_", " ").title()
        color = GROUP_STYLES.get(group, GROUP_STYLES["default"])["color"]
        self.ins_type_lbl.setText(f"  {group_display}  ")
        self.ins_type_lbl.setStyleSheet(
            f"font-size:11px; font-weight:700; padding:2px 8px; border-radius:10px; "
            f"background:{color}22; color:{color}; border:1px solid {color};"
        )
        self.ins_detail_lbl.setText(
            f"ID: {node_id}\nGroup: {group_display}"
        )

    def _generate_graph(self):
        type_map = {0: "multiverse", 1: "universe", 2: "character", 3: "root_entity"}
        idx = self.graph_type_combo.currentIndex()
        gtype = type_map.get(idx, "multiverse")

        entity_id = None
        if gtype != "multiverse":
            entity_id = self.entity_combo.currentData()
            if entity_id is None:
                self.status_label.setText("⚠  Select an entity first")
                return

        # Lock controls
        self._set_controls_enabled(False)
        self.status_label.setText("Building graph…")
        self._show_loading()

        self._worker = GraphWorker(gtype, entity_id)
        self._worker.graph_ready.connect(self._on_graph_ready)
        self._worker.error.connect(self._on_graph_error)
        self._worker.start()

    def _on_graph_ready(self, html_path: str, nx_graph=None):
        # Read & finalize HTML
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()

            # Write to a real file (avoids 2MB setHtml limit)
            final_tmp = tempfile.NamedTemporaryFile(
                suffix=".html", delete=False, prefix="zenai_final_",
                mode="w", encoding="utf-8"
            )
            final_tmp.write(html)
            final_tmp.close()

            # Cleanup previous temp file
            if self._last_tmp_path:
                try:
                    os.unlink(self._last_tmp_path)
                except Exception:
                    pass
            self._last_tmp_path = final_tmp.name

            # Cleanup the intermediate file from worker
            try:
                os.unlink(html_path)
            except Exception:
                pass

            self.web_view.load(QUrl.fromLocalFile(final_tmp.name))
            self._current_nx_graph = nx_graph

        except Exception as e:
            self._on_graph_error(str(e))
            return

        self.status_label.setText(f"✓ Graph ready  ({nx_graph.number_of_nodes() if nx_graph else '?'} nodes)")
        self._set_controls_enabled(True)

        if nx_graph is not None:
            self._populate_table_and_combos(nx_graph)
            # Enable search after graph loads
            self.search_bar.setEnabled(True)
            self.search_bar.clear()

    def _on_graph_error(self, msg: str):
        self.status_label.setText(f"⚠  Error")
        self._set_controls_enabled(True)
        self.web_view.setHtml(_error_html(msg))
        QMessageBox.critical(self, "Graph Error", f"Failed to build graph:\n\n{msg}")

    def _toggle_edit_mode(self, checked: bool):
        if checked:
            self.edit_mode_btn.setText("✓  Editing…")
            self.edit_mode_btn.setStyleSheet(_btn_style_danger())
            js = "if (typeof window.setZenEditMode === 'function') { window.setZenEditMode(true); }"
        else:
            self.edit_mode_btn.setText("✎  Edit Mode")
            self.edit_mode_btn.setStyleSheet(_btn_style())
            js = "if (typeof window.setZenEditMode === 'function') { window.setZenEditMode(false); }"
        self.web_view.page().runJavaScript(js)

    def _export_graph(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Knowledge Graph", "knowledge_graph.html", "HTML (*.html)"
        )
        if not path:
            return
        if self._last_tmp_path and os.path.exists(self._last_tmp_path):
            import shutil
            shutil.copy2(self._last_tmp_path, path)
            QMessageBox.information(self, "Exported", f"Graph saved to:\n{path}")
        else:
            QMessageBox.warning(self, "Nothing to export", "Generate a graph first.")

    def _populate_table_and_combos(self, nx_graph):
        self.table.setRowCount(0)
        self.src_combo.clear()
        self.tgt_combo.clear()

        # Sorted node list for combos
        nodes = sorted(
            ((n_id, d.get("label", str(n_id))) for n_id, d in nx_graph.nodes(data=True)),
            key=lambda x: x[1].lower()
        )
        for n_id, lbl in nodes:
            display = f"{lbl}  ({n_id})"
            self.src_combo.addItem(display, n_id)
            self.tgt_combo.addItem(display, n_id)

        # Edge table
        edge_list = list(nx_graph.edges(data=True))
        self.table.setRowCount(len(edge_list))
        for row, (u, v, data) in enumerate(edge_list):
            u_lbl = nx_graph.nodes[u].get("label", u)
            v_lbl = nx_graph.nodes[v].get("label", v)
            edge_lbl = data.get("label", "")

            src_item = QTableWidgetItem(u_lbl)
            src_item.setFlags(Qt.ItemIsEnabled)
            tgt_item = QTableWidgetItem(f"{v_lbl}  →  {edge_lbl}")
            tgt_item.setFlags(Qt.ItemIsEnabled)

            self.table.setItem(row, 0, src_item)
            self.table.setItem(row, 1, tgt_item)

            del_btn = QPushButton("✕")
            del_btn.setStyleSheet(
                "background:#1a1a1a; color:#E74C3C; border:1px solid #2a2a2a; "
                "border-radius:4px; font-size:12px; font-weight:700;"
                "padding:2px 6px;"
            )
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(
                lambda _, fu=u, tv=v: self._on_manual_del_edge(fu, tv)
            )
            self.table.setCellWidget(row, 2, del_btn)
            self.table.setRowHeight(row, 30)

    def _on_manual_add_edge(self):
        f_id = self.src_combo.currentData()
        t_id = self.tgt_combo.currentData()
        lbl = self.lbl_input.text().strip()
        if not f_id or not t_id:
            self.status_label.setText("⚠  Select source and target")
            return
        self.bridge.add_edge(f_id, t_id, lbl or "Connected")
        self.lbl_input.clear()
        self.status_label.setText("Connection added — regenerating…")
        self._generate_graph()

    def _on_manual_del_edge(self, from_id: str, to_id: str):
        self.bridge.delete_edge_by_nodes(from_id, to_id)
        self.status_label.setText("Connection removed — regenerating…")
        self._generate_graph()

    def _set_controls_enabled(self, enabled: bool):
        self.generate_btn.setEnabled(enabled)
        self.edit_mode_btn.setEnabled(enabled)
        self.add_edge_btn.setEnabled(enabled)
        self.export_btn.setEnabled(enabled)
        if not enabled:
            self.edit_mode_btn.setChecked(False)


# ──────────────────────────────────────────────────────────────────────────────
# HTML Templates for placeholder / loading / error
# ──────────────────────────────────────────────────────────────────────────────
def _placeholder_html() -> str:
    return """
<!DOCTYPE html>
<html>
<head>
<style>
  body {
    background: #141414;
    display: flex; align-items: center; justify-content: center;
    height: 100vh; margin: 0;
    font-family: 'Inter', Arial, sans-serif;
    background-image: radial-gradient(circle at 1px 1px,rgba(255,255,255,0.03)1px,transparent 0);
    background-size: 32px 32px;
  }
  .container { text-align: center; }
  .icon {
    font-size: 64px;
    opacity: 0.12;
    animation: pulse 3s ease-in-out infinite;
  }
  .text { color: #333; font-size: 15px; margin-top: 20px; letter-spacing: 0.5px; }
  .hint { color: #222; font-size: 12px; margin-top: 8px; }
  @keyframes pulse { 0%,100%{opacity:0.08} 50%{opacity:0.18} }
</style>
</head>
<body>
<div class="container">
  <div class="icon">🕸</div>
  <div class="text">Select a graph type and click <strong style="color:#00ADB5">Generate</strong></div>
  <div class="hint">Multiverse · Universe · Character · Root Entity</div>
</div>
</body>
</html>
"""


def _loading_html() -> str:
    return """
<!DOCTYPE html>
<html>
<head>
<style>
  body {
    background: #141414;
    display: flex; align-items: center; justify-content: center;
    height: 100vh; margin: 0;
    font-family: 'Inter', Arial, sans-serif;
  }
  .container { text-align: center; }
  .spinner {
    width: 48px; height: 48px;
    border: 3px solid #1e1e1e;
    border-top-color: #00ADB5;
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
    margin: 0 auto;
  }
  .text { color: #00ADB5; font-size: 14px; margin-top: 20px; letter-spacing: 1px; }
  .sub { color: #333; font-size: 12px; margin-top: 6px; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="container">
  <div class="spinner"></div>
  <div class="text">Building Graph…</div>
  <div class="sub">Querying database and rendering nodes</div>
</div>
</body>
</html>
"""


def _error_html(msg: str) -> str:
    safe_msg = msg.replace("<", "&lt;").replace(">", "&gt;")
    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
  body {{
    background: #141414;
    display: flex; align-items: center; justify-content: center;
    height: 100vh; margin: 0;
    font-family: 'Inter', Arial, sans-serif;
  }}
  .box {{
    text-align: center; max-width: 500px; padding: 32px;
    background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 16px;
  }}
  .icon {{ font-size: 40px; }}
  .title {{ color: #e74c3c; font-size: 16px; font-weight: 700; margin-top: 16px; }}
  .msg {{ color: #666; font-size: 12px; margin-top: 12px; white-space: pre-wrap; }}
</style>
</head>
<body>
<div class="box">
  <div class="icon">⚠</div>
  <div class="title">Graph Build Failed</div>
  <div class="msg">{safe_msg}</div>
</div>
</body>
</html>
"""


# ──────────────────────────────────────────────────────────────────────────────
# Style helpers
# ──────────────────────────────────────────────────────────────────────────────
def _combo_style() -> str:
    return """
        QComboBox {
            background: #1a1a1a;
            color: #EEE;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 13px;
        }
        QComboBox:hover { border-color: #00ADB5; }
        QComboBox::drop-down { border: none; width: 24px; }
        QComboBox QAbstractItemView {
            background: #1a1a1a;
            color: #CCC;
            selection-background-color: #00ADB5;
            border: 1px solid #2a2a2a;
            border-radius: 6px;
        }
    """


def _combo_style_compact() -> str:
    return """
        QComboBox {
            background: #0d0d0d;
            color: #DDD;
            border: 1px solid #1e1e1e;
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
        }
        QComboBox:hover { border-color: #00ADB5; }
        QComboBox::drop-down { border: none; width: 20px; }
        QComboBox QAbstractItemView {
            background: #111;
            color: #CCC;
            selection-background-color: #00ADB5;
            border: 1px solid #1e1e1e;
        }
    """


def _input_style() -> str:
    return """
        QLineEdit {
            background: #0d0d0d;
            color: #DDD;
            border: 1px solid #1e1e1e;
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
        }
        QLineEdit:focus { border-color: #00ADB5; }
    """


def _btn_style() -> str:
    return """
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00ADB5,stop:1 #008C9E);
            color: #0D0D0D;
            font-weight: 800;
            letter-spacing: 0.5px;
            border: none;
            border-radius: 8px;
            padding: 0 18px;
            font-size: 13px;
        }
        QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00d2dc,stop:1 #00a4b8); }
        QPushButton:disabled { background: #1a1a1a; color: #444; }
    """


def _btn_style_secondary() -> str:
    return """
        QPushButton {
            background: #1a1a1a;
            color: #888;
            font-weight: 700;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
            padding: 0 18px;
            font-size: 13px;
        }
        QPushButton:hover { border-color: #00ADB5; color: #EEE; }
        QPushButton:disabled { background: #111; color: #333; border-color: #1a1a1a; }
    """


def _btn_style_danger() -> str:
    return """
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #E74C3C,stop:1 #c0392b);
            color: white;
            font-weight: 800;
            border: none;
            border-radius: 8px;
            padding: 0 18px;
            font-size: 13px;
        }
        QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #ff6b5a,stop:1 #e74c3c); }
    """
