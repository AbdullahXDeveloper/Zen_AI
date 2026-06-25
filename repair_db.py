"""
repair_db.py
One-off script to repair broken SQLite foreign key constraints.

Root cause: migration scripts renamed tables to _old before creating new ones.
SQLite redirected active FK constraints to the _old tables; when _old tables
were dropped the FK references broke. This script rebuilds the affected tables
with clean FK references and migrates the existing data.

Run from the project root:
    python repair_db.py

A timestamped backup of zenai.db is created before any changes.
"""

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "zenai.db"
BACKUP_SUFFIX = datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_db():
    backup_path = DB_PATH.with_name(f"zenai_backup_{BACKUP_SUFFIX}.db")
    shutil.copy2(DB_PATH, backup_path)
    print(f"[Backup] Created: {backup_path}")
    return backup_path


def run_pragma_check(con: sqlite3.Connection) -> list:
    cur = con.execute("PRAGMA foreign_key_check;")
    violations = cur.fetchall()
    return violations


def rebuild_tables(con: sqlite3.Connection):
    """
    Rebuilds tables that may reference _old tables.
    We use the safe 'rename → create → migrate → drop' pattern
    with FK enforcement disabled during the operation.
    """
    con.execute("PRAGMA foreign_keys = OFF;")
    con.execute("BEGIN;")

    tables_to_rebuild = [
        # (table_name, create_sql)
        (
            "characters",
            """CREATE TABLE characters_new (
                id                  INTEGER PRIMARY KEY,
                uuid                VARCHAR(50) NOT NULL UNIQUE,
                universe_id         INTEGER REFERENCES universes(id),
                name                VARCHAR(255) NOT NULL,
                titles              TEXT,
                aliases             TEXT,
                species             VARCHAR(255),
                traits_json         JSON,
                personality         TEXT,
                motivations         TEXT,
                goals               TEXT,
                ideology            TEXT,
                canon_status        VARCHAR(50) DEFAULT 'canon',
                importance_score    INTEGER DEFAULT 50,
                version             INTEGER DEFAULT 1,
                parent_character_id INTEGER REFERENCES characters_new(id),
                faction_id          INTEGER REFERENCES factions(id),
                root_entity_id      INTEGER REFERENCES root_entities(id),
                created_at          DATETIME,
                updated_at          DATETIME
            );""",
        ),
        (
            "character_powers",
            """CREATE TABLE character_powers_new (
                character_id INTEGER NOT NULL REFERENCES characters_new(id),
                power_id     INTEGER NOT NULL REFERENCES powers(id),
                proficiency  INTEGER DEFAULT 50,
                PRIMARY KEY (character_id, power_id)
            );""",
        ),
        (
            "relationships",
            """CREATE TABLE relationships_new (
                id              INTEGER PRIMARY KEY,
                character_a_id  INTEGER NOT NULL REFERENCES characters_new(id),
                character_b_id  INTEGER NOT NULL REFERENCES characters_new(id),
                edge_type       VARCHAR(50) NOT NULL,
                description     TEXT
            );""",
        ),
        (
            "event_participants",
            """CREATE TABLE event_participants_new (
                id          INTEGER PRIMARY KEY,
                event_id    INTEGER NOT NULL REFERENCES events(id),
                entity_type VARCHAR(50) NOT NULL,
                entity_id   INTEGER NOT NULL,
                role        VARCHAR(100)
            );""",
        ),
    ]

    for table_name, create_sql in tables_to_rebuild:
        new_table = f"{table_name}_new"
        print(f"[Rebuild] Rebuilding '{table_name}' ...")

        # Create the new table
        con.execute(create_sql)

        # Get columns that exist in BOTH old and new table (safe migration)
        old_cols = {
            row[1]
            for row in con.execute(f"PRAGMA table_info({table_name});").fetchall()
        }
        new_cols = {
            row[1]
            for row in con.execute(f"PRAGMA table_info({new_table});").fetchall()
        }
        shared_cols = ", ".join(sorted(old_cols & new_cols))

        if shared_cols:
            con.execute(
                f"INSERT INTO {new_table} ({shared_cols}) "
                f"SELECT {shared_cols} FROM {table_name};"
            )

        con.execute(f"DROP TABLE {table_name};")
        con.execute(f"ALTER TABLE {new_table} RENAME TO {table_name};")
        print(f"[Rebuild] '{table_name}' rebuilt successfully.")

    con.execute("COMMIT;")
    con.execute("PRAGMA foreign_keys = ON;")


def main():
    if not DB_PATH.exists():
        print(f"[Error] Database not found at: {DB_PATH}")
        sys.exit(1)

    print(f"[Start] Zen AI DB Repair Tool")
    print(f"[DB Path] {DB_PATH}")

    # ── 1. Backup ──
    backup_db()

    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row

    # ── 2. Check current violations ──
    pre_violations = run_pragma_check(con)
    print(f"\n[Pre-Repair] FK violations found: {len(pre_violations)}")
    for v in pre_violations[:20]:
        print(f"  Table: {v[0]}, RowID: {v[1]}, Parent: {v[2]}, FK Index: {v[3]}")
    if len(pre_violations) > 20:
        print(f"  ... and {len(pre_violations) - 20} more.")

    if not pre_violations:
        print("[OK] No FK violations detected. Database is healthy!")
        con.close()
        return

    # ── 3. Rebuild tables ──
    print("\n[Repair] Rebuilding affected tables...")
    try:
        rebuild_tables(con)
    except Exception as e:
        print(f"\n[Fatal] Repair failed: {e}")
        con.execute("ROLLBACK;")
        con.close()
        sys.exit(1)

    # ── 4. Verify ──
    con2 = sqlite3.connect(str(DB_PATH))
    post_violations = run_pragma_check(con2)
    print(f"\n[Post-Repair] FK violations remaining: {len(post_violations)}")

    if not post_violations:
        print("[SUCCESS] All foreign key constraints are now valid! ✓")
    else:
        print("[WARNING] Some violations remain. Manual inspection needed:")
        for v in post_violations:
            print(f"  {v}")

    con2.close()
    con.close()
    print("\n[Done] Repair complete.")


if __name__ == "__main__":
    main()
