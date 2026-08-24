# main.py
import sys
from PyQt5.QtWidgets import QApplication
from ui.app import DesktopAgentUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DesktopAgentUI()
    window.show()
    sys.exit(app.exec_())