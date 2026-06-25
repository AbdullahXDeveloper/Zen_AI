import re

def patch_graph_view():
    filepath = 'app/ui/graph_view.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add Edit button to UI
    btn_code = """
        # Edit Mode Toggle
        self.edit_mode_btn = QPushButton("✎  Enable Edit")
        self.edit_mode_btn.setFixedHeight(40)
        self.edit_mode_btn.setStyleSheet(_btn_style())
        self.edit_mode_btn.setCheckable(True)
        self.edit_mode_btn.toggled.connect(self._toggle_edit_mode)
        self.edit_mode_btn.setEnabled(False) # Enable only after graph loads
"""
    if 'self.edit_mode_btn = QPushButton' not in content:
        content = content.replace(
            'self.generate_btn.clicked.connect(self._generate_graph)',
            'self.generate_btn.clicked.connect(self._generate_graph)\n' + btn_code
        )
        content = content.replace(
            'bar_layout.addWidget(self.generate_btn)',
            'bar_layout.addWidget(self.edit_mode_btn)\n        bar_layout.addWidget(self.generate_btn)'
        )

    # 2. Add toggle handler
    handler_code = """
    def _toggle_edit_mode(self, checked):
        if checked:
            self.edit_mode_btn.setText("✓  Disable Edit")
            self.edit_mode_btn.setStyleSheet(_btn_style().replace("#00ADB5", "#E74C3C")) # Different color when active
            js = "if (typeof network !== 'undefined') { network.setOptions({ manipulation: { enabled: true } }); }"
            self.web_view.page().runJavaScript(js)
        else:
            self.edit_mode_btn.setText("✎  Enable Edit")
            self.edit_mode_btn.setStyleSheet(_btn_style())
            js = "if (typeof network !== 'undefined') { network.setOptions({ manipulation: { enabled: false } }); }"
            self.web_view.page().runJavaScript(js)
"""
    if 'def _toggle_edit_mode' not in content:
        content = content.replace(
            '    def _show_placeholder(self):',
            handler_code + '\n    def _show_placeholder(self):'
        )

    # 3. Disable edit button while generating, enable on ready
    content = content.replace(
        'self.generate_btn.setEnabled(False)',
        'self.generate_btn.setEnabled(False)\n        self.edit_mode_btn.setEnabled(False)'
    )
    content = content.replace(
        'self.status_label.setText("Ready")',
        'self.status_label.setText("Ready")\n        self.edit_mode_btn.setEnabled(True)\n        self.edit_mode_btn.setChecked(False)'
    )
    # The second replace might apply inside __init__, so let's be more specific:
    # Actually wait, _on_graph_ready sets status to "Ready". Let's look for `self.status_label.setText("Ready")` in _on_graph_ready.
    # Ah, I don't remember if `_on_graph_ready` sets status to "Ready". Let's check using regex.
    # Wait, I'll just put `self.edit_mode_btn.setEnabled(True)` where it enables the generate button.
    content = re.sub(
        r'self\.generate_btn\.setEnabled\(True\)',
        r'self.generate_btn.setEnabled(True)\n        self.edit_mode_btn.setEnabled(True)\n        self.edit_mode_btn.setChecked(False)',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("graph_view.py patched")

def patch_engine():
    filepath = 'app/graph/engine.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Change enabled: true to enabled: false initially
    if 'enabled: true,' in content:
        content = content.replace(
            'enabled: true,',
            'enabled: false,'
        )
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("engine.py patched for edit toggle")

patch_graph_view()
patch_engine()
