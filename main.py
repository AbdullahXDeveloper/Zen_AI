
# import sys
# from PySide6.QtWidgets import QApplication
# from app.database.db_init import init_db
# from app.ui.main_window import ZenMainWindow

# def main():
#     print("[Zen AI] Booting up Operating System...")
    
#     # 1. Start Database
#     init_db()

#     # 2. Start UI Application
#     app = QApplication(sys.argv)
#     app.setStyle("Fusion") # Better look for cross-platform
    
#     # 3. Load Main Window
#     window = ZenMainWindow()
#     window.show()
    
#     print("[Zen AI] System Ready.")
#     sys.exit(app.exec())

# if __name__ == "__main__":
#     main()
# import sys
# from PySide6.QtWidgets import QApplication
# from PySide6.QtGui import QFont
# from PySide6.QtCore import Qt
# from app.database.db_init import init_db
# from app.ui.main_window import ZenMainWindow

# def main():
#     print("[Zen AI] Booting up Operating System...")
#     init_db()

#     # Fix for Blurry Text (High-DPI Scaling)
#     if hasattr(Qt, 'AA_EnableHighDpiScaling'):
#         QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
#     if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
#         QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

#     app = QApplication(sys.argv)
#     app.setStyle("Fusion")
    
#     # Set a Crisp Modern Font Globally
#     app.setFont(QFont("Segoe UI", 11))

#     window = ZenMainWindow()
#     window.show()
    
#     print("[Zen AI] System Ready.")
#     sys.exit(app.exec())

# if __name__ == "__main__":
#     main()

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from app.database.db_init import init_db
from app.ui.main_window import ZenMainWindow

def main():
    print("[Zen AI] Booting up Operating System...")
    init_db()

    # PySide6 mein High-DPI automatically handle ho jata hai
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set a Crisp Modern Font Globally
    app.setFont(QFont("Segoe UI", 11))

    window = ZenMainWindow()
    window.show()
    
    print("[Zen AI] System Ready.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()