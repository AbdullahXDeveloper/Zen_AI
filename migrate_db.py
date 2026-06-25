import sqlite3
import os

def migrate_db():
    db_path = 'data/zenai.db'
    if not os.path.exists(db_path):
        print("Database not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = ['factions', 'locations', 'artifacts', 'events', 'stories']
    columns = ['location_id', 'artifact_id', 'event_id', 'story_id']

    for table in tables:
        for column in columns:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER")
                print(f"Added {column} to {table}")
            except sqlite3.OperationalError as e:
                # Column might already exist
                if "duplicate column name" in str(e):
                    print(f"Column {column} already exists in {table}")
                else:
                    print(f"Error adding {column} to {table}: {e}")

    conn.commit()
    conn.close()
    print("Migration complete!")

migrate_db()
