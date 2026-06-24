import sqlite3
import os
from app.database.db_init import engine
from app.database.models import Base

db_path = 'data/zenai.db'
if not os.path.exists(db_path):
    print("DB not found")
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()

tables_to_migrate = [
    "factions",
    "locations",
    "artifacts",
    "events",
    "stories"
]

c.execute('PRAGMA foreign_keys=off;')
c.execute('BEGIN TRANSACTION;')

for table in tables_to_migrate:
    print(f"Migrating {table}...")
    c.execute(f"ALTER TABLE {table} RENAME TO {table}_old;")

conn.commit()

# Create new tables using SQLAlchemy
print("Creating new schemas...")
Base.metadata.create_all(engine)

# Now copy data
for table in tables_to_migrate:
    print(f"Copying data for {table}...")
    
    # Get columns of the old table
    c.execute(f"PRAGMA table_info({table}_old)")
    columns_info = c.fetchall()
    columns = [col[1] for col in columns_info]
    
    col_str = ", ".join(columns)
    
    c.execute(f"INSERT INTO {table} ({col_str}) SELECT {col_str} FROM {table}_old;")
    c.execute(f"DROP TABLE {table}_old;")

conn.commit()
conn.close()

print('Migration successful')
