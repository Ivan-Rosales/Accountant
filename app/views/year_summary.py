import os
import time
import traceback
from calendar import month_abbr, month_name
from datetime import datetime
from functools import cached_property

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QGridLayout, QComboBox, QWidget

from app.core.settings import QSettings
from app.mixin.async_execution import AsyncExecutionMixin
from app.mixin.property_update import PropertyMixin
from app.widgets.common import QButton, spacer, QProgressButton
from app.widgets.secondary_label import QSecondaryLabel
from base.widget import BaseWidget
from execution.month_summary import MonthSummary
from execution.year_summary import YearSummary


class YearSummaryWorker(QObject):
    start = Signal(object, int, int)
    success = Signal()
    progress = Signal(float)
    error = Signal()

    def on_start(self, client, year, month):
        self.progress.emit(0)

        try:
            year_summary = YearSummary(client, year)
            year_summary.generate_sheet(month)
            year_summary.save()

            self.progress.emit(1)
            self.success.emit()
        except Exception as error:
            self.error.emit(error)
            traceback.print_exc()


class QYearSummary(PropertyMixin, AsyncExecutionMixin, BaseWidget):
    layout_class = QGridLayout
    margin = (5, 5, 5, 5)
    spacing = 4

    worker_class = YearSummaryWorker

    @cached_property
    def client_selector(self):
        return getattr(self.parent(), 'client_selector')

    def __init__(self, *args, **kwargs):
        self._loaded_data = None
        super().__init__(*args, **kwargs)

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
        self.years.currentIndexChanged.connect(self.on_change_year)

        settings = QSettings()
        self.workdir = settings.get_workdir()

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

    def on_change_year(self, _):
        self.load_data(self.client_selector.get_current())

    def load_data(self, client):
        if client is None: return
        current_year = self.years.currentText()
        if self._loaded_data == (client, current_year): return
        self._loaded_data = (client, current_year)

        files_path = self.workdir / client.rfc
        for row, kind in enumerate(('egresos', 'ingresos')):
            file = files_path / f'{client.rfc} {current_year} {kind.upper()}.xlsx'
            summary = MonthSummary(client)
            if file.exists(): summary.from_file(file)

            for month in range(1, 13):
                button: QButton | QWidget = self.buttons.itemAtPosition(row, month).widget()
                button.setProperty('file', file)
                self.set_default(button)

                sheet_name = month_name[month].capitalize()
                if summary.get_sheet(sheet_name):
                    self.set_found(button)

    def set_default(self, button):
        self.setPropertyUpddate(button, 'class', '')
        button.setEnabled(False)

    def set_found(self, button):
        self.setPropertyUpddate(button, 'class', 'primary')
        button.setEnabled(True)

    def btn_click(self, button):
        file = button.property('file')
        if file.exists(): os.startfile(str(file))

    def validate_data(self):
        client = getattr(self.parent(), 'client_selector').get_current()
        year = int(self.years.currentText())
        month = int(self.months.currentIndex() + 1)
        return client, year, month

    def start_worker(self):
        super().start_worker()
        self.execute_btn.setEnabled(False)

    def on_progress(self, progress):
        self.execute_btn.setProgress(progress)

    def on_success(self):
        self.execute_btn.setEnabled(True)

    def on_error(self):
        self.execute_btn.setEnabled(True)
