import locale
import sys

from PySide6 import QtWidgets
from PySide6.QtCore import QThread

from app.core.excepthook import except_hook
from app.workers.database import database_worker
from main import MainWindow

if __name__ == "__main__":
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    sys.excepthook = except_hook

    app = QtWidgets.QApplication([])

    workers = [
        database_worker,
    ]

    thread = QThread()
    for worker in workers:
        worker.moveToThread(thread)
    thread.start()

    widget = MainWindow()
    widget.show()

    sys.exit(app.exec())
