import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from app.database.db_init import init_db, get_session
from app.search.indexer import load_or_rebuild
from app.ui.main_window import ZenMainWindow

def main():
    print("[Zen AI] Booting up Operating System...")
    init_db(seed_root_entities=False)

    # Load (or build) the FAISS vector index so RAG / semantic search works.
    # Without this the index stays empty and the AI answers from general
    # knowledge instead of the Zendrix lore.
    session = get_session()
    try:
        load_or_rebuild(session)
    except Exception as e:
        print(f"[Zen AI] Warning: could not load search index: {e}")
    finally:
        session.close()

    # PySide6 mein High-DPI automatically handle ho jata hai
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set app window icon (logo)
    _logo_path = Path(__file__).parent / "app" / "assets" / "logo.jpg"
    if _logo_path.exists():
        app.setWindowIcon(QIcon(str(_logo_path)))

    # Set a Crisp Modern Font Globally
    app.setFont(QFont("Segoe UI", 11))

    window = ZenMainWindow()

    # Clamp window to available screen geometry to prevent Qt geometry warnings
    screen = app.primaryScreen().availableGeometry()
    win_w  = min(1280, screen.width())
    win_h  = min(800,  screen.height())
    window.resize(win_w, win_h)
    window.move(
        screen.x() + (screen.width()  - win_w) // 2,
        screen.y() + (screen.height() - win_h) // 2,
    )

    window.show()

    print("[Zen AI] System Ready.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()