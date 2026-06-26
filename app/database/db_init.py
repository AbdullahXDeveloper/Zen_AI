"""
ZenAI - Database Initialization
Creates the SQLite database and all tables defined in models.py
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base, RootEntity, Universe

# ------------------------------------------------------------
# Paths-
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "zenai.db")

os.makedirs(DATA_DIR, exist_ok=True)

# ------------------------------------------------------------
# Engine & Session
# ------------------------------------------------------------
DATABASE_URL = f"sqlite:///{DB_PATH}"

from sqlalchemy import event

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 15}  # timeout prevents immediate locks
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db(seed_root_entities: bool = True):
    """Create all tables and optionally seed core Zendrix root entities."""
    Base.metadata.create_all(bind=engine)
    print(f"[ZenAI] Database initialized at: {DB_PATH}")

    if seed_root_entities:
        _seed_defaults()


def _seed_defaults():
    """Seed the known multiversal root entities if they don't exist yet."""
    session = SessionLocal()
    try:
        existing_names = {r.name for r in session.query(RootEntity).all()}

        defaults = [
            {"name": "OM_X", "type": "Root Entity", "description": "Unique multiversal entity.", "importance_score": 100},
            {"name": "K", "type": "Root Entity", "description": "Unique multiversal entity.", "importance_score": 100},
            {"name": "_LA", "type": "Root Entity", "description": "Unique multiversal entity.", "importance_score": 100},
            {"name": "Zendrix Tree", "type": "Cosmic Structure", "description": "The master tree containing all universes (Fruits).", "importance_score": 100},
        ]

        added = 0
        for entry in defaults:
            if entry["name"] not in existing_names:
                session.add(RootEntity(**entry))
                added += 1

        if added:
            session.commit()
            print(f"[ZenAI] Seeded {added} root entities.")
        else:
            print("[ZenAI] Root entities already present, skipping seed.")
    except Exception as e:
        session.rollback()
        print(f"[ZenAI] Seed error: {e}")
    finally:
        session.close()


def get_session():
    """Return a new database session."""
    return SessionLocal()


if __name__ == "__main__":
    init_db()
