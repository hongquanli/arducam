import sys

from PyQt6.QtWidgets import QApplication

from arducam.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow(device_index=0)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
