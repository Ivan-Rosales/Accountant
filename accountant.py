import locale
import sys

from PySide6 import QtWidgets

from app.views.main import MainView

if __name__ == "__main__":
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

    app = QtWidgets.QApplication([])
    widget = MainView()
    widget.show()

    sys.exit(app.exec())
