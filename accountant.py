import sys

from PySide6 import QtWidgets

from app.views.main import MainView

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = MainView()
    widget.show()

    sys.exit(app.exec())
