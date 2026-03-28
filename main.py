import argparse
import sys

from PyQt6.QtWidgets import QApplication

from arducam.gui.main_window import MainWindow


def main():
    parser = argparse.ArgumentParser(description="Arducam IMX586 Controller")
    parser.add_argument("--simulate", action="store_true", help="Run with simulated camera")
    parser.add_argument("--device", type=int, default=0, help="Camera device index")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = MainWindow(device_index=args.device, simulate=args.simulate)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
