import os
import json
import csv
from datetime import datetime

from app.database.models import (
    Universe, CosmicNode, UniverseConnection, RootEntity, RootEntityLink,
    Character, Faction, Location, Power, CharacterPower, Event, EventParticipant,
    RelationshipEdge, Artifact, Story, SimulationRun, EntityLink
)

# List of models to export
MODELS_TO_EXPORT = [
    Universe, CosmicNode, UniverseConnection, RootEntity, RootEntityLink,
    Character, Faction, Location, Power, CharacterPower, Event, EventParticipant,
    RelationshipEdge, Artifact, Story, SimulationRun, EntityLink
]

def _to_dict(obj):
    """Convert an SQLAlchemy model instance to a dictionary."""
    d = {}
    for c in obj.__table__.columns:
        val = getattr(obj, c.name)
        # Convert datetime objects to string format for JSON serialization
        if isinstance(val, datetime):
            d[c.name] = val.isoformat()
        else:
            d[c.name] = val
    return d

def export_database_to_json(session, filepath: str):
    """
    Export the entire database into a single JSON file.
    """
    export_data = {}
    
    for model in MODELS_TO_EXPORT:
        table_name = model.__tablename__
        records = session.query(model).all()
        export_data[table_name] = [_to_dict(r) for r in records]
        
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=4, ensure_ascii=False)


def export_database_to_csv(session, folder_path: str):
    """
    Export the entire database into multiple CSV files inside the given folder.
    """
    # Ensure folder exists
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    for model in MODELS_TO_EXPORT:
        table_name = model.__tablename__
        filepath = os.path.join(folder_path, f"{table_name}.csv")
        records = session.query(model).all()
        
        if not records:
            continue
            
        columns = [c.name for c in model.__table__.columns]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow(columns)
            # Write rows
            for record in records:
                row = []
                for col in columns:
                    val = getattr(record, col)
                    # Convert dicts/lists to JSON strings for CSV compatibility
                    if isinstance(val, (dict, list)):
                        val = json.dumps(val, ensure_ascii=False)
                    row.append(val)
                writer.writerow(row)
