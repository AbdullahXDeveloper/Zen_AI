from app.database.models import Event, EventParticipant, Universe, Character

def get_timeline(session, scope="multiverse", entity_id=None):
    """
    Zendrix lore ki chronological timeline generate karta hai.
    Scope: 'multiverse', 'universe', ya 'character' ho sakta hai.
    """
    events = []

    if scope == "multiverse":
        # Saare universes ke saare events
        events = session.query(Event).all()
        
    elif scope == "universe":
        if not entity_id:
            raise ValueError("Universe scope ke liye entity_id dena zaroori hai.")
        events = session.query(Event).filter(Event.universe_id == entity_id).all()
        
    elif scope == "character":
        if not entity_id:
            raise ValueError("Character scope ke liye entity_id dena zaroori hai.")
        # Pehle wo events dhundo jahan yeh character participant tha
        participants = session.query(EventParticipant).filter(
            EventParticipant.entity_type == "character",
            EventParticipant.entity_id == entity_id
        ).all()
        event_ids = [p.event_id for p in participants]
        # Ab un IDs ki madad se actual events fetch karo
        events = session.query(Event).filter(Event.id.in_(event_ids)).all()
        
    else:
        raise ValueError(f"Unknown scope: {scope}")

    # Output ko format karna
    timeline_data = []
    for e in events:
        # Event mein shaamil entities ka reference
        refs = [
            {"type": p.entity_type, "id": p.entity_id, "role": p.role} 
            for p in e.participants
        ]

        timeline_data.append({
            "event_id": e.id,
            "universe_id": e.universe_id,
            "name": e.name,
            "description": e.description,
            "date_value": e.date_value,
            "date_label": e.date_label,
            "event_type": e.event_type,
            "importance_score": e.importance_score,
            "canon_status": e.canon_status,
            "entity_refs": refs
        })

    # Timeline ko chronologically sort karna (date_value ke hisaab se)
    # Agar date_value None hai toh empty string use karein taake code crash na ho
    timeline_data.sort(key=lambda x: str(x["date_value"]) if x["date_value"] is not None else "")

    return timeline_data