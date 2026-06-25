import re
import glob

def patch_crud_file(filepath, entity_name):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update signature of create_x
    create_func_name = f'def create_{entity_name}('
    if create_func_name in content:
        # insert new fields after root_entity_id: int = None,
        content = content.replace(
            '    root_entity_id: int = None,\n',
            '    root_entity_id: int = None,\n    location_id: int = None,\n    artifact_id: int = None,\n    event_id: int = None,\n    story_id: int = None,\n'
        )
        
    # 2. Update constructor call
    model_class = entity_name.capitalize()
    if entity_name == 'story': model_class = 'Story'
    
    # E.g. fac = Faction(
    #        universe_id=universe_id,
    
    # We can just look for root_entity_id=root_entity_id,
    content = content.replace(
        '        root_entity_id=root_entity_id,\n',
        '        root_entity_id=root_entity_id,\n        location_id=location_id,\n        artifact_id=artifact_id,\n        event_id=event_id,\n        story_id=story_id,\n'
    )
    
    # 3. Update 'allowed' set in update_x
    # allowed = {"universe_id", ...}
    match = re.search(r'allowed\s*=\s*\{([^}]+)\}', content)
    if match:
        allowed_str = match.group(1)
        if '"location_id"' not in allowed_str:
            new_allowed_str = allowed_str + ', "location_id", "artifact_id", "event_id", "story_id"'
            content = content[:match.start(1)] + new_allowed_str + content[match.end(1):]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Patched {filepath}")

patch_crud_file('app/database/crud/factions.py', 'faction')
patch_crud_file('app/database/crud/locations.py', 'location')
patch_crud_file('app/database/crud/artifacts.py', 'artifact')
patch_crud_file('app/database/crud/events.py', 'event')
patch_crud_file('app/database/crud/stories.py', 'story')

