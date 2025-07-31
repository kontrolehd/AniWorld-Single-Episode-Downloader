import sys
from PyQt6.QtWidgets import QApplication
from gui import AniWorldDownloaderGUI

def main():
    app = QApplication(sys.argv)
    window = AniWorldDownloaderGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
