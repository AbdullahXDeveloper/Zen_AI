# """ZenAI application entry point."""

# from app.database.crud import get_stats
# from app.database.db_init import init_db, get_session
# from config.settings import APP_NAME, DB_PATH


# def main() -> None:
#     """Initialize the database and print a short status summary."""
#     print(f"[{APP_NAME}] Starting application...")
#     init_db(seed_root_entities=True)

#     session = get_session()
#     try:
#         stats = get_stats(session)
#         print(f"[{APP_NAME}] Database path: {DB_PATH}")
#         print(f"[{APP_NAME}] Current records: {stats}")
#     finally:
#         session.close()


# if __name__ == "__main__":
#     main()
import sys
from PySide6.QtWidgets import QApplication
from app.database.db_init import init_db
from app.ui.main_window import ZenMainWindow

def main():
    print("[Zen AI] Booting up Operating System...")
    
    # 1. Start Database
    init_db()

    # 2. Start UI Application
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Better look for cross-platform
    
    # 3. Load Main Window
    window = ZenMainWindow()
    window.show()
    
    print("[Zen AI] System Ready.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()