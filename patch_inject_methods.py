import re

def inject_missing_methods():
    filepath = 'app/ui/graph_view.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

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

    insert_marker = "        self.web_view.setHtml(error_html)\n"
    
    if insert_marker in content:
        content = content.replace(insert_marker, insert_marker + "\n" + new_methods)
        print("Successfully injected methods inside the class.")
    else:
        print("Insert marker not found!")
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

inject_missing_methods()
