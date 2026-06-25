import re

def patch_characters_view(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update LoadDependenciesForCharWorker
    content = re.sub(
        r'("locations":\s*\[\{"id": ([^,]+), "name": ([^\}]+)\} for ([^ ]+) in ([^\]]+)\])',
        r'"locations":     [{"id": \2, "name": \3, "universe_id": getattr(\4, "universe_id", None)} for \4 in \5]',
        content
    )
    content = re.sub(
        r'("artifacts":\s*\[\{"id": ([^,]+), "name": ([^\}]+)\} for ([^ ]+) in ([^\]]+)\])',
        r'"artifacts":     [{"id": \2, "name": \3, "universe_id": getattr(\4, "universe_id", None)} for \4 in \5]',
        content
    )
    content = re.sub(
        r'("cosmic_nodes":\s*\[\{"id": ([^,]+), "name": ([^\}]+)\} for ([^ ]+) in ([^\]]+)\])',
        r'"cosmic_nodes":  [{"id": \2, "name": \3, "universe_id": getattr(\4, "universe_id", None)} for \4 in \5]',
        content
    )

    # 2. Inject self._all_deps
    if 'def set_dependencies(self, deps: dict):' in content:
        content = content.replace(
            'def set_dependencies(self, deps: dict):',
            'def set_dependencies(self, deps: dict):\n        self._all_deps = deps'
        )

    # 3. Inject filter call at the end of _on_universe_changed
    if 'def _on_universe_changed(self, idx):' in content:
        lines = content.split('\n')
        in_func = False
        indent = ""
        for i, line in enumerate(lines):
            if 'def _on_universe_changed(self, idx):' in line:
                in_func = True
                indent = line[:len(line) - len(line.lstrip())]
                continue
            if in_func:
                if line.strip() != "" and not line.startswith(indent + " ") and not line.startswith(indent + "\t"):
                    lines.insert(i, indent + "    self._filter_dependency_combos()")
                    in_func = False
                    break
        else:
            if in_func:
                lines.append(indent + "    self._filter_dependency_combos()")
        
        content = '\n'.join(lines)

    # 4. Inject _filter_dependency_combos at the end of the FormPanel class
    filter_func = """
    def _filter_dependency_combos(self):
        uid = self.universe_combo.currentData() if hasattr(self, "universe_combo") else None
        if not hasattr(self, '_all_deps') or not self._all_deps:
            return
        
        def _repopulate(combo, key, current_val):
            if combo is None: return
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("None", None)
            idx_to_select = 0
            for item in self._all_deps.get(key, []):
                if uid is None or item.get("universe_id") == uid or item.get("universe_id") is None:
                    combo.addItem(item["name"], item["id"])
                    if item["id"] == current_val:
                        idx_to_select = combo.count() - 1
            combo.setCurrentIndex(idx_to_select)
            combo.blockSignals(False)

        if hasattr(self, 'location_combo'): _repopulate(self.location_combo, "locations", self.location_combo.currentData())
        if hasattr(self, 'artifact_combo'): _repopulate(self.artifact_combo, "artifacts", self.artifact_combo.currentData())
        if hasattr(self, 'cosmic_node_combo'): _repopulate(self.cosmic_node_combo, "cosmic_nodes", self.cosmic_node_combo.currentData())
"""
    if 'def _filter_dependency_combos' not in content:
        lines = content.split('\n')
        in_panel = False
        inserted = False
        for i, line in enumerate(lines):
            if re.match(r'^class .*FormPanel\(.*\):', line):
                in_panel = True
                continue
            if in_panel:
                if line.strip() != "" and not line.startswith(" ") and not line.startswith("\t"):
                    lines.insert(i, filter_func)
                    inserted = True
                    break
        if in_panel and not inserted:
            lines.append(filter_func)
            
        content = '\n'.join(lines)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Patched {filepath}")

import os
# ensure stories_view.py and artifacts_view.py are restored
os.system("git restore app/ui/stories_view.py")
os.system("git restore app/ui/artifacts_view.py")
os.system("git restore app/ui/characters_view.py")

patch_characters_view('app/ui/characters_view.py')
