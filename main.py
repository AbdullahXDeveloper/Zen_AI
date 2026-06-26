import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont, QIcon
import traceback

def global_exception_hook(exctype, value, tb):
    """Catch unhandled exceptions and show them in a GUI dialog."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    print(f"[CRITICAL ERROR]\n{err_msg}")
    
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle("Zen_OS Critical Error")
    msg_box.setText("An unexpected error occurred.")
    msg_box.setInformativeText(str(value))
    msg_box.setDetailedText(err_msg)
    msg_box.exec()

sys.excepthook = global_exception_hook

from app.database.db_init import init_db, get_session
from app.search.indexer import load_or_rebuild
from app.ui.main_window import ZenMainWindow

def main():
    print("[Zen_OS v4] Booting up Operating System...")
    init_db(seed_root_entities=False)

    # Load (or build) the FAISS vector index so RAG / semantic search works.
    # Without this the index stays empty and the AI answers from general
    # knowledge instead of the Zendrix lore.
    session = get_session()
    try:
        load_or_rebuild(session)
    except Exception as e:
        print(f"[Zen_OS v4] Warning: could not load search index: {e}")
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

    print("[Zen_OS v4] System Ready.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()