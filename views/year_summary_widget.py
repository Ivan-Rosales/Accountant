from calendar import month_name
from collections import defaultdict

from PySide6.QtWidgets import QGridLayout

from app.core.base_widget import BaseWidget
from app.widgets.common import QButton, spacer


class QYearSummary(BaseWidget):
    layout_class = QGridLayout
    margin = (5, 5, 5, 5)
    spacing = 0

    def create_ui(self):
        self.buttons = defaultdict(dict)
        for kind in ('egresos', 'ingresos'):
            for month in range(1, 13):
                label = f'{kind} {month}'
                btn = QButton(month_name[month], self, fn=lambda _, x=label: print(x))
                btn.setProperty('scope', 'table')
                self.buttons[kind][month] = btn

        self.execute = QButton('hola', self)
        self.execute.setProperty('class', 'primary')

    def load_ui(self, layout: QGridLayout):
        layout.addItem(spacer, 0, 0, 1, 12)

        count_rows = len(self.buttons.values())

        is_top = True
        for row, buttons in enumerate(self.buttons.values(), 1):
            is_left = True
            is_bottom = row == count_rows
            count_cols = len(buttons.values()) - 1
            for month, btn in enumerate(buttons.values()):
                layout.addWidget(btn, row, month)

                is_right = month == count_cols
                if is_top and is_left: btn.setProperty('corner', 'top-left')
                if is_top and is_right: btn.setProperty('corner', 'top-right')
                if is_bottom and is_left: btn.setProperty('corner', 'bottom-left')
                if is_bottom and is_right: btn.setProperty('corner', 'bottom-right')

                is_left = False
            is_top = False

        layout.addItem(spacer, 3, 0, 1, 12)
        layout.addWidget(self.execute, 4, 0, 1, 12)


"""

    def create_ui(self):
        self.buttons_layout = QGridLayout()

        for i in range(1, 13):
            btn_1 = QButton(month_name[i], self, fn=lambda _, x=i: print(f'btn_1 {x}'))
            btn_2 = QButton(month_name[i], self, fn=lambda _, x=i: print(f'btn_2 {x}'))
            self.buttons_layout.addWidget(btn_1, 0, i)
            self.buttons_layout.addWidget(btn_2, 1, i)

        self.buttons = QWidget()
        self.buttons.setLayout(self.buttons_layout)

        self.execute = QButton('hola', self)

    def load_ui(self, layout):
        layout.addWidget(self.buttons)
        layout.addItem(spacer)
        layout.addWidget(self.execute)
"""
