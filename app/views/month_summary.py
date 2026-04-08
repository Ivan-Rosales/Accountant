from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QVBoxLayout

from app.mixin.async_execution import AsyncExecutionMixin
from app.widgets.common import QButton, spacer
from app.widgets.confirm_box import QConfirmMessageBox
from app.widgets.file_selector import QFileSelector
from app.widgets.metrics import QMetrics
from base.popup import QDialogException
from base.widget import BaseWidget
from models import Cliente
from worker.month_summary import MonthSummary
from worker.zip_file import ZipFile


class MonthSummaryWorker(QObject):
    start = Signal(list, object)
    success = Signal(object, int)
    error = Signal(object)

    def on_start(self, paths, client: Cliente):
        try:
            summary = None
            n_files = len(paths)
            for path in paths:
                zipfile = ZipFile(path)
                data_path = zipfile.extract()

                summary = MonthSummary(client)
                summary.add_files_in_folder(data_path)
                summary.save()

            self.success.emit(summary, n_files)
        except Exception as error:
            self.error.emit(error)


class QMonthSummary(AsyncExecutionMixin, BaseWidget):
    layout_class = QVBoxLayout
    margin = (5, 5, 5, 5)

    worker_class = MonthSummaryWorker

    def create_ui(self):
        self.selector = QFileSelector(self, filter="*.zip")

        self.metrics = QMetrics(self)
        self.execute_btn = QButton('ejecutar', self, fn=self.start_worker)
        self.execute_btn.setProperty('class', 'primary')

    def load_ui(self, layout):
        layout.addItem(spacer)
        layout.addWidget(self.selector)
        layout.addItem(spacer)

        layout.addWidget(self.metrics)
        layout.addWidget(self.execute_btn)

    def validate_data(self):
        client = self.parent().client_selector.get_current()
        get_paths = self.selector.get_files()
        return get_paths, client

    def start_worker(self):
        super().start_worker()
        self.execute_btn.setEnabled(False)

    def on_error(self, error):
        self.execute_btn.setEnabled(True)
        if not isinstance(error, QDialogException): return
        raise QDialogException(self, str(error), format=False)

    def on_success(self, summary, n_files):
        self.execute_btn.setEnabled(True)
        self.metrics.add_registers_today(n_files)
        self.selector.clear()

        title = '¿Desea abrirlo?'
        message = f'Se generó correctamente.\n{summary.filename}\n{title}'
        QConfirmMessageBox(self, message, summary.startfile, title=title)
