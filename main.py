import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


class AgentWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FGO AI Assistant")
        self.setWindowOpacity(0.9)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(420, 200)

        layout = QVBoxLayout()
        label = QLabel("FGO AI Assistant is ready.\nConnect to Ollama to start the ReAct loop.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setLayout(layout)


def main() -> None:
    app = QApplication(sys.argv)
    window = AgentWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
