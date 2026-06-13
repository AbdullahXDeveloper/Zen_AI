"""ZenAI application entry point."""

from app.database.crud import get_stats
from app.database.db_init import init_db, get_session
from config.settings import APP_NAME, DB_PATH


def main() -> None:
    """Initialize the database and print a short status summary."""
    print(f"[{APP_NAME}] Starting application...")
    init_db(seed_root_entities=True)

    session = get_session()
    try:
        stats = get_stats(session)
        print(f"[{APP_NAME}] Database path: {DB_PATH}")
        print(f"[{APP_NAME}] Current records: {stats}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
