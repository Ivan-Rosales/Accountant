from calendar import month_abbr
from datetime import datetime

from PySide6.QtWidgets import QGridLayout, QComboBox

from app.core.base_widget import BaseWidget
from app.widgets.common import QButton, spacer
from core.configuration import Settings


class QYearSummary(BaseWidget):
    layout_class = QGridLayout
    margin = (5, 5, 5, 5)
    spacing = 4

    def create_ui(self):
        self.buttons = QGridLayout()
        self.buttons.setSpacing(0)

        last_row = 1
        last_col = 11
        corners = {
            (0, 0): 'top-left',
            (0, last_col): 'top-right',
            (last_row, 0): 'bottom-left',
            (last_row, last_col): 'bottom-right',
        }

        for row, kind in enumerate(('egresos', 'ingresos')):
            for month in range(12):
                btn = QButton(month_abbr[month + 1], self)
                btn.setProperty('scope', 'table')
                if corner := corners.get((row, month)):
                    btn.setProperty('corner', corner)
                self.buttons.addWidget(btn, row, month)

        now = datetime.now()

        self.years = QComboBox(self)
        self.years.addItems([str(now.year + i) for i in range(-5, 6)])
        self.years.setCurrentIndex(5)

        self.months = QComboBox(self)
        self.months.addItems([str(i) for i in range(1, 13)])
        self.months.setCurrentIndex(now.month - 1)

        self.execute = QButton('ejecutar', self)
        self.execute.setProperty('class', 'primary')

        settings = Settings()

        func = lambda i: self.years.setCurrentIndex(int(i))
        settings.register_setting('year-selector', self.years.currentIndex, func)

        func = lambda i: self.months.setCurrentIndex(int(i))
        settings.register_setting('month-selector', self.months.currentIndex, func)

    def load_ui(self, layout: QGridLayout):
        layout.addItem(spacer, 0, 0, 1, 12)
        layout.addLayout(self.buttons, 1, 0, 1, 12)
        layout.addWidget(self.years, 2, 0, 1, 6)
        layout.addWidget(self.months, 2, 6, 1, 6)
        layout.addItem(spacer, 3, 0, 1, 12)

        layout.addWidget(self.execute, 4, 0, 1, 12)
