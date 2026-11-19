from calendar import month_name
from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMessageBox

from app.core.settings import settings
from app.widgets.message_dialog import QMessageDialog
from app.widgets.switch import QClickComboBox
from base.widget import BaseWidget


class QPeriodSelector(BaseWidget):
    """Año y mes; emite `changed(year, month)`. Con `cache_key` recuerda la selección entre sesiones."""
    changed = Signal(int, int)
    windows_size = None

    def __init__(self, *args, **kwargs):
        self.cache_key = kwargs.pop('cache_key', None)
        super().__init__(*args, **kwargs)

    def create_ui(self):
        now = datetime.now()
        self.years = QClickComboBox(self)
        self.years.addItems([str(now.year + i) for i in range(-5, 2)])
        self.years.setCurrentText(str(now.year))

        self.months = QClickComboBox(self)
        self.months.addItems([month_name[i].capitalize() for i in range(1, 13)])
        self.months.setCurrentIndex(now.month - 1)

        if self.cache_key:
            def set_year(value):
                if self.years.findText(str(value)) < 0: raise ValueError(value)
                self.years.setCurrentText(str(value))

            def set_month(value):
                index = int(value)
                if not 0 <= index < 12: raise ValueError(value)
                self.months.setCurrentIndex(index)

            settings.register_setting(f'{self.cache_key}-year', self.years.currentText, set_year,
                                      str(now.year), signal=self.years.currentIndexChanged)
            settings.register_setting(f'{self.cache_key}-month', self.months.currentIndex, set_month,
                                      now.month - 1, signal=self.months.currentIndexChanged)

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
