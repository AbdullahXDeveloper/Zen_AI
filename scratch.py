import sqlite3

def find_entities():
    conn = sqlite3.connect('data/zenai.db')
    cursor = conn.cursor()
    
    # Let's list all tables first to see where data is
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    print("Tables:", tables)
    
    for t in tables:
        try:
            # Let's try to query 'name' if column exists
            cursor.execute(f"PRAGMA table_info({t})")
            columns = [c[1] for c in cursor.fetchall()]
            if 'name' in columns:
                cursor.execute(f"SELECT * FROM {t} WHERE name LIKE '%K%' OR name LIKE '%_LA%' OR name LIKE '%Zendrix%' OR name LIKE '%OM_X%'")
                rows = cursor.fetchall()
                if rows:
                    print(f"\n--- Matches in table '{t}' ---")
                    for r in rows:
                        print(r)
        except Exception as e:
            pass

find_entities()
