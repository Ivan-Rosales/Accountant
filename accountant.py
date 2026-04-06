import locale
import sys

from PySide6 import QtWidgets

from app.core.excepthook import except_hook
from main import MainView

if __name__ == "__main__":
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    sys.excepthook = except_hook

    app = QtWidgets.QApplication([])
    widget = MainView()
    widget.show()

    sys.exit(app.exec())
