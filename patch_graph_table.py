import re

def patch_graph_view_table():
    filepath = 'app/ui/graph_view.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add missing imports
    import_repl = "from PySide6.QtWidgets import (\n    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,\n    QLabel, QComboBox, QFrame, QSizePolicy, QSpinBox, QMessageBox, QInputDialog,\n    QSplitter, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit\n)"
    content = re.sub(r'from PySide6\.QtWidgets import \([\s\S]*?\)', import_repl, content)

    # 1. Add layout and splitter
    splitter_code = """
        # --- Root Layout Splitter ---
        self.splitter = QSplitter(Qt.Vertical)
        
        # ── WebEngine View ──
        self.web_view = QWebEngineView()
        self.page = CustomWebEnginePage(self.web_view.page().profile(), self.web_view)
        self.web_view.setPage(self.page)
        self.web_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.web_view.setStyleSheet("background: #1E1E1E;")
        
        # Configure Bridge
        self.bridge = GraphBridge()
        self.page.bridge = self.bridge
        
        self._show_placeholder()
        
        self.splitter.addWidget(self.web_view)

        # ── Data Table Editor Panel ──
        self.editor_panel = QWidget()
        self.editor_panel.setStyleSheet("background: #111111; border-top: 1px solid #333;")
        ed_layout = QVBoxLayout(self.editor_panel)
        ed_layout.setContentsMargins(10, 10, 10, 10)
        
        ed_title = QLabel("Manual Knowledge Graph Editor")
        ed_title.setStyleSheet("color: #00ADB5; font-size: 14px; font-weight: bold; border: none;")
        ed_layout.addWidget(ed_title)
        
        # Add Edge Form
        add_form = QHBoxLayout()
        self.src_combo = QComboBox()
        self.src_combo.setMinimumWidth(150)
        self.src_combo.setStyleSheet(_combo_style())
        self.tgt_combo = QComboBox()
        self.tgt_combo.setMinimumWidth(150)
        self.tgt_combo.setStyleSheet(_combo_style())
        self.lbl_input = QLineEdit()
        self.lbl_input.setPlaceholderText("Connection Label (e.g. Member, Friend)")
        self.lbl_input.setStyleSheet("background: #1E1E1E; color: #FFF; border: 1px solid #333; padding: 4px; border-radius: 4px;")
        self.add_edge_btn = QPushButton("Add Connection")
        self.add_edge_btn.setStyleSheet(_btn_style())
        self.add_edge_btn.clicked.connect(self._on_manual_add_edge)
        
        add_form.addWidget(QLabel("Source:", styleSheet="color:#CCC; border:none;"))
        add_form.addWidget(self.src_combo)
        add_form.addWidget(QLabel("Target:", styleSheet="color:#CCC; border:none;"))
        add_form.addWidget(self.tgt_combo)
        add_form.addWidget(QLabel("Label:", styleSheet="color:#CCC; border:none;"))
        add_form.addWidget(self.lbl_input)
        add_form.addWidget(self.add_edge_btn)
        
        ed_layout.addLayout(add_form)
        
        # Table Widget
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Source ID", "Target ID", "Label", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet(\"\"\"
            QTableWidget { background: #1A1A1A; color: #DDD; border: 1px solid #333; }
            QHeaderView::section { background: #222; color: #00ADB5; font-weight: bold; padding: 4px; border: 1px solid #333; }
        \"\"\")
        ed_layout.addWidget(self.table)
        
        self.splitter.addWidget(self.editor_panel)
        
        root_layout.addWidget(control_bar)
        root_layout.addWidget(self.splitter)
"""
    # Replace the old layout code
    old_layout_regex = r'# ── WebEngine View ──[\s\S]*?root_layout\.addWidget\(self\.web_view\)'
    content = re.sub(old_layout_regex, splitter_code.strip(), content)

    # 2. Update `GraphWorker` to also return nx_graph edges and nodes for the table
    # Wait, GraphWorker already has `self.nx_graph`. 
    # The signal `graph_ready` sends `(str, nx.Graph)`. Wait, does it send `nx.Graph`? Let's check `GraphWorker`.
    # `graph_ready = Signal(str)` -> Only path string. We need to pass nodes and edges, or just keep `nx_graph` in `GraphWorker` and pass it back.
    # Let's change `graph_ready = Signal(str)` to `graph_ready = Signal(str, object)`

    content = content.replace("graph_ready = Signal(str)", "graph_ready = Signal(str, object)")
    content = content.replace("self.graph_ready.emit(output_path)", "self.graph_ready.emit(output_path, G)")
    
    # 3. Update `_on_graph_ready` signature
    content = content.replace("def _on_graph_ready(self, html_path):", "def _on_graph_ready(self, html_path, nx_graph=None):")
    
    # Inside _on_graph_ready, call `_populate_table`
    populate_call = """
        self.status_label.setText("Ready")
        self.edit_mode_btn.setEnabled(True)
        self.edit_mode_btn.setChecked(False)
        
        if nx_graph is not None:
            self._populate_table_and_combos(nx_graph)
"""
    content = re.sub(r'self\.status_label\.setText\("Ready"\)\s*self\.edit_mode_btn\.setEnabled\(True\)\s*self\.edit_mode_btn\.setChecked\(False\)', populate_call.strip(), content)

    # 4. Add methods for table populating, adding and deleting
    new_methods = """
    def _populate_table_and_combos(self, nx_graph):
        self.table.setRowCount(0)
        self.src_combo.clear()
        self.tgt_combo.clear()
        
        # Populate combos with sorted nodes
        nodes = []
        for n_id, n_data in nx_graph.nodes(data=True):
            lbl = n_data.get('label', n_id)
            nodes.append((n_id, lbl))
        nodes.sort(key=lambda x: x[1])
        
        for n_id, lbl in nodes:
            display_text = f"{lbl} ({n_id})"
            self.src_combo.addItem(display_text, n_id)
            self.tgt_combo.addItem(display_text, n_id)
            
        # Populate table
        edges = nx_graph.edges(data=True)
        self.table.setRowCount(len(edges))
        for row, (u, v, data) in enumerate(edges):
            u_lbl = nx_graph.nodes[u].get('label', u)
            v_lbl = nx_graph.nodes[v].get('label', v)
            edge_lbl = data.get('label', '')
            
            self.table.setItem(row, 0, QTableWidgetItem(f"{u_lbl} [{u}]"))
            self.table.setItem(row, 1, QTableWidgetItem(f"{v_lbl} [{v}]"))
            self.table.setItem(row, 2, QTableWidgetItem(edge_lbl))
            
            del_btn = QPushButton("Delete")
            del_btn.setStyleSheet("background: #E74C3C; color: white; border: none; padding: 4px; border-radius: 3px;")
            # Capture u, v in lambda
            del_btn.clicked.connect(lambda _, from_id=u, to_id=v: self._on_manual_del_edge(from_id, to_id))
            self.table.setCellWidget(row, 3, del_btn)

    def _on_manual_add_edge(self):
        f_id = self.src_combo.currentData()
        t_id = self.tgt_combo.currentData()
        lbl = self.lbl_input.text().strip()
        
        if not f_id or not t_id:
            return
            
        self.bridge.add_edge(f_id, t_id, lbl)
        self.lbl_input.clear()
        # Refresh graph
        self._generate_graph()

    def _on_manual_del_edge(self, from_id, to_id):
        self.bridge.delete_edge_by_nodes(from_id, to_id)
        # Refresh graph
        self._generate_graph()
"""
    # Append the new methods to the class
    # The class ends near the end of the file, let's inject it before `# ─────────────────────────────────────────────` at the end
    content = re.sub(r'(# ─────────────────────────────────────────────\s*$)', new_methods + r'\1', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("graph_view.py patched with table editor")

patch_graph_view_table()
