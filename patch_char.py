import sqlite3
import os
import re

# 1. Update models.py for Character
filepath = 'app/database/models.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r'class Character\(Base\):\n    __tablename__ = "characters"\n'
match = re.search(pattern, content)
if match:
    insert_idx = match.end()
    fk_pattern = r'    root_entity_id = Column\(Integer, ForeignKey\("root_entities.id"\), index=True, nullable=True\)\n'
    fk_match = re.search(fk_pattern, content[insert_idx:])
    if fk_match:
        insert_pos_fk = insert_idx + fk_match.end()
        new_fks = (
            '    location_id = Column(Integer, ForeignKey("locations.id"), index=True, nullable=True)\n'
            '    artifact_id = Column(Integer, ForeignKey("artifacts.id"), index=True, nullable=True)\n'
            '    event_id = Column(Integer, ForeignKey("events.id"), index=True, nullable=True)\n'
            '    story_id = Column(Integer, ForeignKey("stories.id"), index=True, nullable=True)\n'
        )
        if 'location_id = Column' not in content[insert_idx:insert_idx+1000]:
            content = content[:insert_pos_fk] + new_fks + content[insert_pos_fk:]

            rel_pattern = r'    root_entity = relationship\("RootEntity", foreign_keys=\[root_entity_id\], backref="characters"\)\n'
            rel_match = re.search(rel_pattern, content)
            if rel_match:
                insert_pos_rel = rel_match.end()
                rels = (
                    '    location = relationship("Location", foreign_keys=[location_id])\n'
                    '    artifact = relationship("Artifact", foreign_keys=[artifact_id])\n'
                    '    event = relationship("Event", foreign_keys=[event_id])\n'
                    '    story = relationship("Story", foreign_keys=[story_id])\n'
                )
                content = content[:insert_pos_rel] + rels + content[insert_pos_rel:]

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print("models.py patched for Character")

# 2. Update characters table in zenai.db
db_path = 'data/zenai.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for column in ['location_id', 'artifact_id', 'event_id', 'story_id']:
        try:
            cursor.execute(f"ALTER TABLE characters ADD COLUMN {column} INTEGER")
            print(f"Added {column} to characters")
        except sqlite3.OperationalError:
            print(f"Column {column} already exists in characters")
    conn.commit()
    conn.close()

# 3. Update crud/characters.py
filepath = 'app/database/crud/characters.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

if 'location_id' not in content:
    content = content.replace(
        '    root_entity_id: int = None,\n',
        '    root_entity_id: int = None,\n    location_id: int = None,\n    artifact_id: int = None,\n    event_id: int = None,\n    story_id: int = None,\n'
    )
    content = content.replace(
        '        root_entity_id=root_entity_id,\n',
        '        root_entity_id=root_entity_id,\n        location_id=location_id,\n        artifact_id=artifact_id,\n        event_id=event_id,\n        story_id=story_id,\n'
    )
    match = re.search(r'allowed\s*=\s*\{([^}]+)\}', content)
    if match:
        allowed_str = match.group(1)
        new_allowed_str = allowed_str + ', "location_id", "artifact_id", "event_id", "story_id"'
        content = content[:match.start(1)] + new_allowed_str + content[match.end(1):]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("crud/characters.py patched")

# 4. Patch characters_view.py
filepath = 'app/ui/characters_view.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# LoadDependenciesForCharWorker
content = content.replace(
    'arts = session.query(models.Artifact).all()',
    'arts = session.query(models.Artifact).all()\n            evts = session.query(models.Event).all()\n            stys = session.query(models.Story).all()'
)
content = content.replace(
    '"artifacts":     [{"id": x.id, "name": x.name, "universe_id": getattr(x, "universe_id", None)} for x in arts],\n                "cosmic_nodes":  [{"id": x.id, "name": x.name, "universe_id": getattr(x, "universe_id", None)} for x in nodes]',
    '"artifacts":     [{"id": x.id, "name": x.name, "universe_id": getattr(x, "universe_id", None)} for x in arts],\n                "events":        [{"id": x.id, "name": x.name, "universe_id": getattr(x, "universe_id", None)} for x in evts],\n                "stories":       [{"id": x.id, "name": getattr(x, "title", getattr(x, "name", "")), "universe_id": getattr(x, "universe_id", None)} for x in stys],\n                "cosmic_nodes":  [{"id": x.id, "name": x.name, "universe_id": getattr(x, "universe_id", None)} for x in nodes]'
)

# QComboBoxes
setup_combo = '''
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
if 'self.event_combo = QComboBox()' not in content:
    content = content.replace(
        'self.artifact_combo.setStyleSheet(fs)\n        lay.addWidget(self.artifact_combo)',
        'self.artifact_combo.setStyleSheet(fs)\n        lay.addWidget(self.artifact_combo)\n' + setup_combo
    )

# Clear combos
clear_combos = '''
        self.event_combo.blockSignals(True)
        self.event_combo.clear()
        self.event_combo.addItem("None", None)
        self.event_combo.blockSignals(False)

        self.story_combo.blockSignals(True)
        self.story_combo.clear()
        self.story_combo.addItem("None", None)
        self.story_combo.blockSignals(False)
'''
if 'self.event_combo.blockSignals(True)' not in content:
    content = content.replace(
        'self.artifact_combo.addItem("None", None)\n        self.artifact_combo.blockSignals(False)',
        'self.artifact_combo.addItem("None", None)\n        self.artifact_combo.blockSignals(False)\n' + clear_combos
    )

# set_dependencies
if 'for item in deps.get("events", []):' not in content:
    content = content.replace(
        'for item in deps.get("artifacts", []):\n            self.artifact_combo.addItem(item["name"], item["id"])',
        'for item in deps.get("artifacts", []):\n            self.artifact_combo.addItem(item["name"], item["id"])\n        for item in deps.get("events", []):\n            self.event_combo.addItem(item["name"], item["id"])\n        for item in deps.get("stories", []):\n            self.story_combo.addItem(item["name"], item["id"])'
    )

# load_data
if 'self.event_combo.itemData(i) == data.get("event_id")' not in content:
    load_data = '''
        for i in range(self.event_combo.count()):
            if self.event_combo.itemData(i) == data.get("event_id"):
                self.event_combo.setCurrentIndex(i)
        for i in range(self.story_combo.count()):
            if self.story_combo.itemData(i) == data.get("story_id"):
                self.story_combo.setCurrentIndex(i)
'''
    content = content.replace(
        'self.artifact_combo.setCurrentIndex(i)',
        'self.artifact_combo.setCurrentIndex(i)\n' + load_data
    )

# get_form_data
if '"event_id": self.event_combo.currentData()' not in content:
    content = content.replace(
        '"artifact_id": self.artifact_combo.currentData(),',
        '"artifact_id": self.artifact_combo.currentData(),\n            "event_id": self.event_combo.currentData(),\n            "story_id": self.story_combo.currentData(),'
    )

# _filter_dependency_combos
if 'if hasattr(self, \'event_combo\'): _repopulate' not in content:
    content = content.replace(
        'if hasattr(self, \'artifact_combo\'): _repopulate(self.artifact_combo, "artifacts", self.artifact_combo.currentData())',
        'if hasattr(self, \'artifact_combo\'): _repopulate(self.artifact_combo, "artifacts", self.artifact_combo.currentData())\n        if hasattr(self, \'event_combo\'): _repopulate(self.event_combo, "events", self.event_combo.currentData())\n        if hasattr(self, \'story_combo\'): _repopulate(self.story_combo, "stories", self.story_combo.currentData())'
    )

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("characters_view.py patched")
