import json
import os
from app.database.db_init import get_session, init_db
from app.lore.pipeline import ingest_text, summarize_result
from app.lore.review import approve_all

def run():
    init_db(seed_root_entities=False)
    session = get_session()
    
    file_path = os.path.join("data", "Zendrix_Master_Archive.md")
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return
        
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    if not text:
        print("No raw_lore_text found.")
        return
        
    print(f"Ingesting text of length {len(text)}...")
    result = ingest_text(session, text, source_name="Zendrix_Master_Archive")
    
    print(summarize_result(result))
    
    # Auto approve all
    merged = result["merged_result"]
    approved_indices = {
        "character": list(range(len(merged.get("characters", [])))),
        "faction": list(range(len(merged.get("factions", [])))),
        "location": list(range(len(merged.get("locations", [])))),
        "event": list(range(len(merged.get("events", [])))),
        "artifact": list(range(len(merged.get("artifacts", [])))),
        "relationships": list(range(len(merged.get("relationships", [])))),
    }
    
    # Create or get a default universe
    from app.database.models import Universe
    uni = session.query(Universe).filter_by(name="Zendrix Master").first()
    if not uni:
        uni = Universe(name="Zendrix Master", description="Imported from Master Archive")
        session.add(uni)
        session.commit()
    
    print("Auto-approving all extracted entities...")
    approve_result = approve_all(session, merged, approved_indices, universe_id=uni.id)
    
    for key, items in approve_result.get("created", {}).items():
        print(f"Persisted {len(items)} {key}(s) to DB.")
        
    session.commit()
    session.close()
    print("Done!")

if __name__ == "__main__":
    run()
