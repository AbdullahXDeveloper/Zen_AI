import json
import os
import sys

# Ensure imports work from Zen_AI root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.db_init import get_session
from app.database.models import Universe, Character, Location, Faction

def run_bulk_import(json_file="bulk_data.json"):
    if not os.path.exists(json_file):
        print(f"File {json_file} not found!")
        return

    print(f"Reading data from {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    session = get_session()
    
    universes_added = 0
    characters_added = 0
    locations_added = 0
    factions_added = 0

    try:
        for u_data in data.get("universes", []):
            u_name = u_data.get("name")
            
            # Check if universe already exists
            uni = session.query(Universe).filter_by(name=u_name).first()
            if not uni:
                uni = Universe(
                    name=u_name,
                    description=u_data.get("description", ""),
                    canon_status=u_data.get("canon_status", "canon"),
                    importance_score=u_data.get("importance_score", 50)
                )
                session.add(uni)
                session.commit() # Commit to get Universe ID
                universes_added += 1
                print(f"[+] Added Universe: {u_name}")
            else:
                print(f"[~] Universe already exists: {u_name} (Skipping creation)")

            # Characters
            for c_data in u_data.get("characters", []):
                char = Character(
                    universe_id=uni.id,
                    name=c_data.get("name"),
                    species=c_data.get("species", ""),
                    personality=c_data.get("personality", ""),
                    importance_score=c_data.get("importance_score", 50)
                )
                session.add(char)
                characters_added += 1

            # Locations
            for l_data in u_data.get("locations", []):
                loc = Location(
                    universe_id=uni.id,
                    name=l_data.get("name"),
                    type=l_data.get("type", ""),
                    description=l_data.get("description", "")
                )
                session.add(loc)
                locations_added += 1

            # Factions
            for f_data in u_data.get("factions", []):
                fac = Faction(
                    universe_id=uni.id,
                    name=f_data.get("name"),
                    ideology=f_data.get("ideology", "")
                )
                session.add(fac)
                factions_added += 1

        # Final commit for all the children entities
        session.commit()
        
        print("\n=== BULK IMPORT SUCCESSFUL ===")
        print(f"Universes Created : {universes_added}")
        print(f"Characters Created: {characters_added}")
        print(f"Locations Created : {locations_added}")
        print(f"Factions Created  : {factions_added}")
        print("==============================\n")

    except Exception as e:
        session.rollback()
        print(f"Error during import: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    run_bulk_import()
