from exceptions import ValidationException
from calendar import month_abbr, month_name
from datetime import datetime
from functools import cached_property
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGridLayout, QComboBox, QWidget, QMessageBox
from openpyxl import load_workbook

from app.core.settings import settings
from app.core.tasks import TaskRunner
from app.mixin.async_execution import AsyncExecutionMixin
from app.mixin.property_update import PropertyMixin
from app.widgets.common import QButton, spacer, QProgressButton
from app.widgets.toast import toast
from app.widgets.loader import QLoadingOverlay
from app.widgets.period_selector import show_message
from app.widgets.secondary_label import QSecondaryLabel
from app.workers.watch_dog import WatchdogWorker
from app.workers.year_summary import YearSummaryWorker
from base.tab import TabWidget
from execution.month_summary import MonthSummary
from logger import logger


class QYearSummary(PropertyMixin, AsyncExecutionMixin, TabWidget):
    layout_class = QGridLayout
    tooltip_label = 'concentrado anual'
    page_title = 'Concentrado anual'
    page_subtitle = 'Meses generados del año y cálculo del IVA mensual y bimestral'

    worker_class = YearSummaryWorker
    busy_message = 'Generando concentrado anual...'
    RELOAD_DELAY_MS = 700

    @cached_property
    def client_selector(self):
        return getattr(self.parent(), 'client_selector')

    def __init__(self, *args, **kwargs):
        self.workdir = settings.get_workdir()
        super().__init__(*args, **kwargs)
        self.tasks = TaskRunner(self)
        self.loader = QLoadingOverlay(self)

        # Varios eventos seguidos del sistema de archivos (p. ej. al guardar un libro) se agrupan en una recarga
        self.reload_timer = QTimer(self)
        self.reload_timer.setSingleShot(True)
        self.reload_timer.setInterval(self.RELOAD_DELAY_MS)
        self.reload_timer.timeout.connect(self.request_load)

        self.watchdog = WatchdogWorker(self.workdir)
        self.watchdog.change.connect(self.reload_data)
        self.watchdog.on_start()
        self.destroyed.connect(self.watchdog.stop)

    def set_workdir(self, path):
        self.workdir = settings.get_workdir() if path is None else Path(str(path))
        self.watchdog.set_path(self.workdir)
        self.reload_data()

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

        self.execute_btn = QProgressButton('generar concentrado anual', self, fn=self.start_worker)
        self.execute_btn.setProperty('class', 'primary')
        self.execute_btn.setMinimumHeight(40)

        self.client_selector.on_change(self.request_load)
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

    def reload_data(self, *_):
        timer = getattr(self, 'reload_timer', None)  # puede llamarse desde create_ui, antes de crear el timer
        if timer is not None: timer.start()

    @staticmethod
    def get_sheetnames(file: Path) -> list:
        # Modo solo lectura: abre únicamente el índice de hojas, no carga las celdas
        workbook = load_workbook(file, read_only=True)
        try:
            return list(workbook.sheetnames)
        finally:
            workbook.close()

    def load_data(self, client=None):
        if not hasattr(self, 'tasks'):  # aún construyéndose
            self._stale = True
            return
        client = client or self.client_selector.get_current()
        if client is None: return

        current_year = self.years.currentText()
        logger.debug(f'{self.__class__.__name__} loading data for client {client} and year {current_year}')

        files_path = self.workdir / client.rfc
        files = [files_path / f'{client.rfc} {current_year} {kind.upper()}.xlsx' for kind in ('egresos', 'ingresos')]

        def read():
            result = []
            for file in files:
                try:
                    result.append(self.get_sheetnames(file) if file.exists() else [])
                except Exception as error:
                    logger.error(f'{self.__class__.__name__} cannot load data {error}')
                    result.append([])
            return result

        self.tasks.run('load', read, on_done=lambda names: self.show_months(files, names),
                       overlay=self.loader, message='Revisando concentrados...')

    def show_months(self, files, sheetnames_by_kind):
        for row, (file, sheetnames) in enumerate(zip(files, sheetnames_by_kind)):
            for month in range(1, 13):
                button: QButton | QWidget = self.buttons.itemAtPosition(row, month).widget()
                button.setProperty('file', str(file))
                button.setProperty('month', month)
                self.set_default(button)

                if month_name[month].capitalize() in sheetnames:
                    self.set_found(button)

    def set_default(self, button):
        self.setPropertyUpddate(button, 'class', '')
        button.setEnabled(False)
        kind = 'ingresos' if str(button.property('file')).endswith('INGRESOS.xlsx') else 'egresos'
        button.setToolTip(f'Sin concentrado de {kind} de {month_name[button.property("month")]}. '
                          f'Genérelo en la pestaña mensual.')

    def set_found(self, button):
        self.setPropertyUpddate(button, 'class', 'primary')
        button.setEnabled(True)
        button.setToolTip(f'Abrir {month_name[button.property("month")]}')

    def btn_click(self, button):
        client = self.client_selector.get_current()
        if client is None: return
        month = button.property('month')
        summary = MonthSummary(client)
        summary.from_file(Path(button.property('file')))

        logger.debug(f'{self.__class__.__name__} opening summary {summary} {month}')

        sheet_name = month_name[month].capitalize()

        def failed(error):
            show_message(self, str(error), icon=QMessageBox.Icon.Warning, title='No se pudo abrir')

        # Marcar la hoja activa reescribe el libro: se hace en segundo plano y luego se abre Excel
        self.tasks.run('open', lambda: summary.set_active_sheet(sheet_name), on_done=lambda _: summary.startfile(),
                       on_error=failed, overlay=self.loader, message=f'Abriendo {sheet_name}...')

    def validate_data(self):
        client = getattr(self.parent(), 'client_selector').get_current()
        if client is None:
            raise ValidationException('Seleccione un cliente')
        year = int(self.years.currentText())
        month = int(self.months.currentIndex() + 1)
        return client, year, month

    def on_success(self, summary):
        logger.debug(f'{self.__class__.__name__} generation success {summary}')

        self.execute_btn.setEnabled(True)
        self.execute_btn.resetProgress()

        toast(self, 'Concentrado anual generado', detail=summary.filename.name, action=('Abrir', summary.startfile))
