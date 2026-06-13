from app.database.db_init import init_db, get_session
from app.database.models import Universe, Character, Faction, Event, EventParticipant, RelationshipEdge, Location

def seed_data():
    print("Database session start ho raha hai...")
    init_db()
    session = get_session()

    # Check agar data pehle se majood hai taake duplicate na ho
    if session.query(Character).filter_by(name="Raven").first():
        print("⚠️ Dummy data pehle se database mein majood hai!")
        return

    print("Dummy data insert ho raha hai...")

    # 1. Universe Create Karo
    uni = Universe(name="Zendrix Prime", description="The main testing universe", importance_score=90)
    session.add(uni)
    session.commit() # Commit taake ID mil jaye

    # 2. Characters Create Karo
    raven = Character(universe_id=uni.id, name="Raven", species="Human", importance_score=85)
    kael = Character(universe_id=uni.id, name="Kael", species="Elf", importance_score=70)
    session.add_all([raven, kael])
    session.commit()

    # 3. Faction Create Karo
    shadows = Faction(universe_id=uni.id, name="The Shadow Vanguard", founder_id=raven.id)
    session.add(shadows)

    # 4. Location Create Karo
    hollow_court = Location(universe_id=uni.id, name="Hollow Court", type="Stronghold")
    session.add(hollow_court)
    session.commit()

    # 5. Relationship (Graph Edge)
    rel = RelationshipEdge(
        character_a_id=raven.id, 
        character_b_id=kael.id, 
        edge_type="enemy", 
        description="Rivals since the first era."
    )
    session.add(rel)

    # 6. Events (Timeline ke liye)
    evt1 = Event(universe_id=uni.id, name="The Awakening", date_value="0001", date_label="Year 1, Era of Light", event_type="birth")
    evt2 = Event(universe_id=uni.id, name="Battle of Hollow Court", date_value="0302", date_label="Year 302, Era of Fire", event_type="war")
    session.add_all([evt1, evt2])
    session.commit()

    # 7. Event Participants (Events ko characters/locations se connect karna)
    p1 = EventParticipant(event_id=evt2.id, entity_type="character", entity_id=raven.id, role="attacker")
    p2 = EventParticipant(event_id=evt2.id, entity_type="character", entity_id=kael.id, role="defender")
    p3 = EventParticipant(event_id=evt2.id, entity_type="location", entity_id=hollow_court.id, role="battleground")
    session.add_all([p1, p2, p3])
    session.commit()

    print("✅ Dummy data successfully add ho gaya hai!")

if __name__ == "__main__":
    seed_data()