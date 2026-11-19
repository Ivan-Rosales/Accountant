from calendar import month_name
from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QMessageBox

from app.widgets.message_dialog import QMessageDialog
from base.widget import BaseWidget


class QPeriodSelector(BaseWidget):
    """Año y mes; emite `changed(year, month)`."""
    changed = Signal(int, int)
    windows_size = None

    def create_ui(self):
        now = datetime.now()
        self.years = QComboBox(self)
        self.years.addItems([str(now.year + i) for i in range(-5, 2)])
        self.years.setCurrentText(str(now.year))

        self.months = QComboBox(self)
        self.months.addItems([month_name[i].capitalize() for i in range(1, 13)])
        self.months.setCurrentIndex(now.month - 1)

        self.years.currentIndexChanged.connect(self._emit)
        self.months.currentIndexChanged.connect(self._emit)

    def load_ui(self, layout):
        layout.addWidget(self.years)
        layout.addWidget(self.months)

    @property
    def year(self) -> int:
        return int(self.years.currentText())

    @property
    def month(self) -> int:
        return self.months.currentIndex() + 1

    def _emit(self, *_):
        self.changed.emit(self.year, self.month)


def show_message(parent, text, detail='', icon=QMessageBox.Icon.Information, title='Información'):
    message = QMessageDialog(parent)
    message.setIcon(icon)
    message.setWindowTitle(title)
    message.setText(text)
    if detail: message.setDetailedText(detail)
    message.exec()
