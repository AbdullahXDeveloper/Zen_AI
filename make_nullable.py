import sqlite3
import os

db_path = 'data/zenai.db'
if not os.path.exists(db_path):
    print("DB not found")
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute('PRAGMA foreign_keys=off;')
c.execute('BEGIN TRANSACTION;')
c.execute('ALTER TABLE characters RENAME TO characters_old;')
c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='characters_old'")
sql = c.fetchone()[0]
sql = sql.replace('characters_old', 'characters')
sql = sql.replace('universe_id INTEGER NOT NULL', 'universe_id INTEGER')
c.execute(sql)
c.execute('INSERT INTO characters SELECT * FROM characters_old;')
c.execute('DROP TABLE characters_old;')
conn.commit()
conn.close()
print('Migration successful')
