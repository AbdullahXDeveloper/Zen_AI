import re

def patch_ui_files():
    views = ['factions', 'locations', 'artifacts', 'events', 'stories']
    for view in views:
        filepath = f'app/ui/{view}_view.py'
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 1. Patch LoadParentsWorker
        if 'facs = session.query(models.Faction).all()' in content:
            content = content.replace(
                'facs = session.query(models.Faction).all()\n            roots = session.query(models.RootEntity).all()',
                'facs = session.query(models.Faction).all()\n            roots = session.query(models.RootEntity).all()\n            locs = session.query(models.Location).all()\n            arts = session.query(models.Artifact).all()\n            evts = session.query(models.Event).all()\n            stys = session.query(models.Story).all()'
            )
            content = content.replace(
                '"factions": [{"id": f.id, "name": f.name} for f in facs],\n                "root_entities": [{"id": r.id, "name": r.name} for r in roots]',
                '"factions": [{"id": f.id, "name": f.name, "universe_id": getattr(f, "universe_id", None)} for f in facs],\n                "root_entities": [{"id": r.id, "name": r.name} for r in roots],\n                "locations": [{"id": x.id, "name": x.name, "universe_id": getattr(x, "universe_id", None)} for x in locs],\n                "artifacts": [{"id": x.id, "name": x.name, "universe_id": getattr(x, "universe_id", None)} for x in arts],\n                "events": [{"id": x.id, "name": x.name, "universe_id": getattr(x, "universe_id", None)} for x in evts],\n                "stories": [{"id": x.id, "name": getattr(x, "title", getattr(x, "name", "")), "universe_id": getattr(x, "universe_id", None)} for x in stys]'
            )

        # 2. Patch _setup_ui in FormPanel
        # Find self.root_entity_combo = QComboBox()
        # and insert the new combos
        setup_combo = '''
        lbl = QLabel("LOCATION")
        lbl.setStyleSheet("color: #777777; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        lay.addWidget(lbl)
        self.location_combo = QComboBox()
        self.location_combo.setStyleSheet(fs)
        lay.addWidget(self.location_combo)
        
        lbl = QLabel("ARTIFACT")
        lbl.setStyleSheet("color: #777777; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        lay.addWidget(lbl)
        self.artifact_combo = QComboBox()
        self.artifact_combo.setStyleSheet(fs)
        lay.addWidget(self.artifact_combo)

        lbl = QLabel("EVENT")
        lbl.setStyleSheet("color: #777777; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        lay.addWidget(lbl)
        self.event_combo = QComboBox()
        self.event_combo.setStyleSheet(fs)
        lay.addWidget(self.event_combo)

        lbl = QLabel("STORY")
        lbl.setStyleSheet("color: #777777; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        lay.addWidget(lbl)
        self.story_combo = QComboBox()
        self.story_combo.setStyleSheet(fs)
        lay.addWidget(self.story_combo)
'''
        if 'self.location_combo = QComboBox()' not in content:
            content = content.replace(
                'self.root_entity_combo = QComboBox()\n        self.root_entity_combo.setStyleSheet(fs)\n        lay.addWidget(self.root_entity_combo)',
                'self.root_entity_combo = QComboBox()\n        self.root_entity_combo.setStyleSheet(fs)\n        lay.addWidget(self.root_entity_combo)\n' + setup_combo
            )

        # 3. Patch set_parents
        content = content.replace(
            'def set_parents(self, universes: list, factions: list, root_entities: list):',
            'def set_parents(self, universes: list, factions: list, root_entities: list, locations: list, artifacts: list, events: list, stories: list):'
        )
        content = content.replace(
            'self._root_entities = root_entities',
            'self._root_entities = root_entities\n        self._locations = locations\n        self._artifacts = artifacts\n        self._events = events\n        self._stories = stories\n        self._all_deps = {"factions": factions, "locations": locations, "artifacts": artifacts, "events": events, "stories": stories}'
        )
        # Clear combos
        if 'self.root_entity_combo.blockSignals(False)' in content and 'self.location_combo.blockSignals(False)' not in content:
            clear_combos = '''
        self.location_combo.blockSignals(True)
        self.location_combo.clear()
        self.location_combo.addItem("None", None)
        self.location_combo.blockSignals(False)

        self.artifact_combo.blockSignals(True)
        self.artifact_combo.clear()
        self.artifact_combo.addItem("None", None)
        self.artifact_combo.blockSignals(False)

        self.event_combo.blockSignals(True)
        self.event_combo.clear()
        self.event_combo.addItem("None", None)
        self.event_combo.blockSignals(False)

        self.story_combo.blockSignals(True)
        self.story_combo.clear()
        self.story_combo.addItem("None", None)
        self.story_combo.blockSignals(False)
'''
            content = content.replace(
                'self.root_entity_combo.addItem(r["name"], r["id"])\n        self.root_entity_combo.blockSignals(False)',
                'self.root_entity_combo.addItem(r["name"], r["id"])\n        self.root_entity_combo.blockSignals(False)\n' + clear_combos
            )

        # Set selection in load_data
        if 'for i in range(self.root_entity_combo.count()):' in content and 'for i in range(self.location_combo.count()):' not in content:
            load_data = '''
        for i in range(self.location_combo.count()):
            if self.location_combo.itemData(i) == data.get("location_id"):
                self.location_combo.setCurrentIndex(i)
        for i in range(self.artifact_combo.count()):
            if self.artifact_combo.itemData(i) == data.get("artifact_id"):
                self.artifact_combo.setCurrentIndex(i)
        for i in range(self.event_combo.count()):
            if self.event_combo.itemData(i) == data.get("event_id"):
                self.event_combo.setCurrentIndex(i)
        for i in range(self.story_combo.count()):
            if self.story_combo.itemData(i) == data.get("story_id"):
                self.story_combo.setCurrentIndex(i)
'''
            content = content.replace(
                'self.root_entity_combo.setCurrentIndex(i)',
                'self.root_entity_combo.setCurrentIndex(i)\n' + load_data
            )

        # get_form_data
        content = content.replace(
            '"root_entity_id": rid,',
            '"root_entity_id": rid,\n            "location_id": self.location_combo.currentData(),\n            "artifact_id": self.artifact_combo.currentData(),\n            "event_id": self.event_combo.currentData(),\n            "story_id": self.story_combo.currentData(),'
        )

        # 4. _on_parents_loaded in Main Widget
        content = content.replace(
            'self._root_entities = data["root_entities"]',
            'self._root_entities = data["root_entities"]\n        self._locations = data.get("locations", [])\n        self._artifacts = data.get("artifacts", [])\n        self._events = data.get("events", [])\n        self._stories = data.get("stories", [])'
        )
        content = content.replace(
            'self._form_panel.set_parents(self._universes, self._all_factions, self._root_entities)',
            'self._form_panel.set_parents(self._universes, self._all_factions, self._root_entities, self._locations, self._artifacts, self._events, self._stories)'
        )

        # 5. Connect filter dependencies
        if 'def _filter_dependency_combos' not in content:
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

        if hasattr(self, 'faction_combo'): _repopulate(self.faction_combo, "factions", self.faction_combo.currentData())
        if hasattr(self, 'location_combo'): _repopulate(self.location_combo, "locations", self.location_combo.currentData())
        if hasattr(self, 'artifact_combo'): _repopulate(self.artifact_combo, "artifacts", self.artifact_combo.currentData())
        if hasattr(self, 'event_combo'): _repopulate(self.event_combo, "events", self.event_combo.currentData())
        if hasattr(self, 'story_combo'): _repopulate(self.story_combo, "stories", self.story_combo.currentData())
"""
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
            
            # Now call it on universe change
            # find _on_universe_changed and put it at the end
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

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {filepath}")

patch_ui_files()
