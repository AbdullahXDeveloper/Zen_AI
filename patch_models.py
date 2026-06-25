import re

def patch_models():
    filepath = 'app/database/models.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    classes_to_patch = ['Faction', 'Location', 'Artifact', 'Event', 'Story']

    for cls in classes_to_patch:
        # Find the class definition and its properties
        pattern = f'class {cls}\\(Base\\):\n    __tablename__ = "[^"]+"\n'
        match = re.search(pattern, content)
        if not match:
            print(f"Could not find {cls}")
            continue

        insert_idx = match.end()
        # Find where to insert foreign keys (after root_entity_id)
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
            content = content[:insert_pos_fk] + new_fks + content[insert_pos_fk:]

        # Reload after modifying content
        match = re.search(pattern, content)
        insert_idx = match.end()
        
        # Find where to insert relationships (after root_entity)
        rel_pattern = r'    root_entity = relationship\("RootEntity", foreign_keys=\[root_entity_id\]\)\n'
        rel_match = re.search(rel_pattern, content[insert_idx:])
        if rel_match:
            insert_pos_rel = insert_idx + rel_match.end()
            
            rels = []
            if cls == 'Location':
                rels.append('    parent_location = relationship("Location", foreign_keys=[location_id], remote_side="Location.id")\n')
            else:
                rels.append('    location = relationship("Location", foreign_keys=[location_id])\n')
                
            if cls == 'Artifact':
                rels.append('    parent_artifact = relationship("Artifact", foreign_keys=[artifact_id], remote_side="Artifact.id")\n')
            else:
                rels.append('    artifact = relationship("Artifact", foreign_keys=[artifact_id])\n')
                
            if cls == 'Event':
                rels.append('    parent_event = relationship("Event", foreign_keys=[event_id], remote_side="Event.id")\n')
            else:
                rels.append('    event = relationship("Event", foreign_keys=[event_id])\n')
                
            if cls == 'Story':
                rels.append('    parent_story = relationship("Story", foreign_keys=[story_id], remote_side="Story.id")\n')
            else:
                rels.append('    story = relationship("Story", foreign_keys=[story_id])\n')
            
            content = content[:insert_pos_rel] + "".join(rels) + content[insert_pos_rel:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("models.py patched!")

patch_models()
