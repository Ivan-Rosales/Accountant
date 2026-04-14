import os
from calendar import month_abbr, month_name
from datetime import datetime
from functools import cached_property

from PySide6.QtWidgets import QGridLayout, QComboBox, QWidget

from app.core.settings import settings
from app.mixin.async_execution import AsyncExecutionMixin
from app.mixin.property_update import PropertyMixin
from app.widgets.common import QButton, spacer, QProgressButton
from app.widgets.confirm_box import QConfirmMessageBox
from app.widgets.secondary_label import QSecondaryLabel
from app.workers.watch_dog import WatchdogWorker
from app.workers.year_summary_worker import YearSummaryWorker
from base.widget import BaseWidget
from execution.month_summary import MonthSummary


class QYearSummary(PropertyMixin, AsyncExecutionMixin, BaseWidget):
    layout_class = QGridLayout
    margin = (5, 5, 5, 5)
    spacing = 4

    worker_class = [YearSummaryWorker, WatchdogWorker(settings.get_workdir())]

    @cached_property
    def client_selector(self):
        return getattr(self.parent(), 'client_selector')

    def __init__(self, *args, **kwargs):
        self.workdir = settings.get_workdir()
        super().__init__(*args, **kwargs)

        if hasattr(self, 'worker_1'):
            self.worker_1.change.connect(self.reload_data)
            self.worker_1.start.emit()

    def create_ui(self):
        self.buttons = QGridLayout()
        self.buttons.setSpacing(0)

        self.label_egresos = QSecondaryLabel('Egresos', self)
        self.buttons.addWidget(self.label_egresos, 0, 0)

        self.label_ingresos = QSecondaryLabel('Ingresos', self)
        self.buttons.addWidget(self.label_ingresos, 1, 0)

        last_row = 1
        last_col = 12
        corners = {
            (0, 1): 'top-left',
            (0, last_col): 'top-right',
            (last_row, 1): 'bottom-left',
            (last_row, last_col): 'bottom-right',
        }

        for row, kind in enumerate(('egresos', 'ingresos')):
            for month in range(1, 13):
                btn = QButton(month_abbr[month], self)
                btn.clicked.connect(lambda _, button=btn: self.btn_click(button))
                btn.setProperty('scope', 'table')
                btn.setDisabled(True)

                if corner := corners.get((row, month)):
                    btn.setProperty('corner', corner)

                self.buttons.addWidget(btn, row, month)

        now = datetime.now()

        self.years = QComboBox(self)
        self.years.addItems([str(now.year + i) for i in range(-5, 6)])
        self.years.setCurrentIndex(5)

        self.months = QComboBox(self)
        self.months.addItems([month_name[i].capitalize() for i in range(1, 13)])
        self.months.setCurrentIndex(now.month - 1)

        self.execute_btn = QProgressButton('ejecutar', self, fn=self.start_worker)
        self.execute_btn.setProperty('class', 'primary')

        self.client_selector.on_change(self.load_data)
        self.years.currentIndexChanged.connect(self.reload_data)

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

        layout.addWidget(self.execute_btn, 4, 0, 1, 12)

    def reload_data(self, _):
        self.load_data(self.client_selector.get_current())

    def load_data(self, client):
        if client is None: return
        current_year = self.years.currentText()
        files_path = self.workdir / client.rfc
        for row, kind in enumerate(('egresos', 'ingresos')):
            file = files_path / f'{client.rfc} {current_year} {kind.upper()}.xlsx'

            try:
                summary = MonthSummary(client)
                if file.exists(): summary.from_file(file)

                for month in range(1, 13):
                    button: QButton | QWidget = self.buttons.itemAtPosition(row, month).widget()
                    button.setProperty('summary', summary)
                    button.setProperty('month', month)
                    self.set_default(button)

                    sheet_name = month_name[month].capitalize()
                    if summary.get_sheet(sheet_name):
                        self.set_found(button)
            except:
                continue

    def set_default(self, button):
        self.setPropertyUpddate(button, 'class', '')
        button.setEnabled(False)

    def set_found(self, button):
        self.setPropertyUpddate(button, 'class', 'primary')
        button.setEnabled(True)

    def btn_click(self, button):
        summary = button.property('summary')
        month = button.property('month')
        sheet_name = month_name[month].capitalize()
        summary.set_active_sheet(sheet_name)

        summary.startfile()

    def validate_data(self):
        client = getattr(self.parent(), 'client_selector').get_current()
        year = int(self.years.currentText())
        month = int(self.months.currentIndex() + 1)
        return client, year, month

    def on_success(self, summary):
        self.execute_btn.setEnabled(True)
        self.execute_btn.resetProgress()

        title = '¿Desea abrirlo?'
        message = f'Se generó correctamente.\n{summary.filename}\n{title}'
        QConfirmMessageBox(self, message, summary.startfile, title=title)
