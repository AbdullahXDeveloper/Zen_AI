import re

def patch_cosmic_view():
    filepath = 'app/ui/cosmic_view.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_get_parent = """            def get_parent_info(item):
                pid = "center"
                pname = "Zendrix Prime"
                if getattr(item, "universe_id", None):
                    pid = f"uni_{item.universe_id}"
                    pname = item.universe.name if hasattr(item, "universe") and item.universe else "Universe"
                elif getattr(item, "faction_id", None):
                    pid = f"fac_{item.faction_id}"
                    pname = item.faction.name if hasattr(item, "faction") and item.faction else "Faction"
                elif getattr(item, "location_id", None):
                    pid = f"loc_{item.location_id}"
                    pname = item.location.name if hasattr(item, "location") and item.location else "Location"
                elif getattr(item, "artifact_id", None):
                    pid = f"art_{item.artifact_id}"
                    pname = item.artifact.name if hasattr(item, "artifact") and item.artifact else "Artifact"
                elif getattr(item, "event_id", None):
                    pid = f"evt_{item.event_id}"
                    pname = item.event.name if hasattr(item, "event") and item.event else "Event"
                elif getattr(item, "story_id", None):
                    pid = f"sto_{item.story_id}"
                    pname = item.story.title if hasattr(item, "story") and hasattr(item.story, "title") else "Story"
                elif getattr(item, "root_entity_id", None):
                    pid = f"root_{item.root_entity_id}"
                    pname = item.root_entity.name if hasattr(item, "root_entity") and item.root_entity else "Root Entity"
                return pid, pname"""
                
    old_get_parent = """            def get_parent_info(item):
                pid = "center"
                pname = "Zendrix Prime"
                if getattr(item, "universe_id", None):
                    pid = f"uni_{item.universe_id}"
                    pname = item.universe.name if hasattr(item, "universe") and item.universe else "Universe"
                elif getattr(item, "faction_id", None):
                    pid = f"fac_{item.faction_id}"
                    pname = item.faction.name if hasattr(item, "faction") and item.faction else "Faction"
                elif getattr(item, "root_entity_id", None):
                    pid = f"root_{item.root_entity_id}"
                    pname = item.root_entity.name if hasattr(item, "root_entity") and item.root_entity else "Root Entity"
                return pid, pname"""

    if old_get_parent in content:
        content = content.replace(old_get_parent, new_get_parent)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("cosmic_view.py patched")
    else:
        print("Could not find get_parent_info in cosmic_view.py")

def patch_graph_engine():
    filepath = 'app/graph/engine.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Let's add linking logic in build_universe_graph. We can add a generic block at the end of build_universe_graph
    
    insert_point_regex = r'(    # 7\. Add Universal Links \(EntityLinks\))'
    
    match = re.search(insert_point_regex, content)
    if match:
        insert_idx = match.start(1)
        
        new_logic = """
    # 6b. Add Parent Links for all entities
    # Connect entities to their faction_id, location_id, artifact_id, event_id, story_id, root_entity_id
    entities_lists = [
        (characters, "chr"),
        (factions, "fac"),
        (locations, "loc"),
        (artifacts, "art"),
        (events, "evt"),
        (stories, "sto")
    ]
    for ent_list, prefix in entities_lists:
        for ent in ent_list:
            ent_id = f"{prefix}_{ent.id}"
            if not G.has_node(ent_id): continue
            
            if getattr(ent, "faction_id", None) and G.has_node(f"fac_{ent.faction_id}") and prefix != "fac":
                G.add_edge(ent_id, f"fac_{ent.faction_id}", label="member_of", title="Linked Faction")
            if getattr(ent, "location_id", None) and G.has_node(f"loc_{ent.location_id}") and prefix != "loc":
                G.add_edge(ent_id, f"loc_{ent.location_id}", label="located_at", title="Linked Location")
            if getattr(ent, "artifact_id", None) and G.has_node(f"art_{ent.artifact_id}") and prefix != "art":
                G.add_edge(ent_id, f"art_{ent.artifact_id}", label="holds_artifact", title="Linked Artifact")
            if getattr(ent, "event_id", None) and G.has_node(f"evt_{ent.event_id}") and prefix != "evt":
                G.add_edge(ent_id, f"evt_{ent.event_id}", label="part_of_event", title="Linked Event")
            if getattr(ent, "story_id", None) and G.has_node(f"sto_{ent.story_id}") and prefix != "sto":
                G.add_edge(ent_id, f"sto_{ent.story_id}", label="featured_in", title="Linked Story")

"""
        if "6b. Add Parent Links" not in content:
            content = content[:insert_idx] + new_logic + content[insert_idx:]
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print("app/graph/engine.py patched")
        else:
            print("Already patched engine.py")
    else:
        print("Could not find insertion point in engine.py")

patch_cosmic_view()
patch_graph_engine()
