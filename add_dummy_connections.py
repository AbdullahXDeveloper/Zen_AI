# import os
# import sys

# # Ensure imports work from Zen_AI root
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from app.database.db_init import get_session
# from app.database.models import Universe, Character, Faction, RelationshipEdge, RootEntity, RootEntityLink

# def add_dummy_connections():
#     session = get_session()
    
#     # 1. Connect Characters within the same universe
#     universes = session.query(Universe).all()
#     for u in universes:
#         chars = session.query(Character).filter_by(universe_id=u.id).all()
#         factions = session.query(Faction).filter_by(universe_id=u.id).all()
        
#         # Make the first character the founder of the first faction
#         if chars and factions:
#             factions[0].founder_id = chars[0].id
            
#         # Connect characters to each other
#         if len(chars) >= 2:
#             # Connect char 0 and char 1
#             existing_edge = session.query(RelationshipEdge).filter_by(
#                 character_a_id=chars[0].id, character_b_id=chars[1].id
#             ).first()
            
#             if not existing_edge:
#                 edge = RelationshipEdge(
#                     character_a_id=chars[0].id,
#                     character_b_id=chars[1].id,
#                     edge_type="enemy",
#                     description="Sworn enemies since the Great War"
#                 )
#                 session.add(edge)
                
#     # 2. Connect Root Entities to Universes
#     root_entities = session.query(RootEntity).all()
#     if root_entities and universes:
#         # Link first root entity to first universe
#         link = RootEntityLink(
#             root_entity_id=root_entities[0].id,
#             entity_type="universe",
#             entity_id=universes[0].id,
#             description="The Creator watches over this realm"
#         )
#         session.add(link)

#     session.commit()
#     print("Added dummy connections successfully!")
#     session.close()

# if __name__ == "__main__":
#     add_dummy_connections()
