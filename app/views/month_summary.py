import traceback

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QVBoxLayout, QCheckBox

from app.mixin.async_execution import AsyncExecutionMixin
from app.widgets.common import spacer, QProgressButton
from app.widgets.confirm_box import QConfirmMessageBox
from app.widgets.file_selector import QFileSelector
from app.widgets.metrics import QMetrics
from base.popup import QDialogException
from base.widget import BaseWidget
from logger import logger
from models import Cliente
from worker.month_summary import MonthSummary
from worker.zip_file import ZipFile


class MonthSummaryWorker(QObject):
    start = Signal(list, object, object)
    success = Signal(object, int)
    progress = Signal(float)
    error = Signal(object)

    default_params = {
        'create_providers': False,
    }

    @staticmethod
    def get_steps(base_steps, params):
        if params['create_providers']:
            base_steps *= 2

        return base_steps

    def on_start(self, paths, client: Cliente, params=None):
        params = self.default_params | (params or {})
        create_providers = params['create_providers']

        self.progress.emit(0)

        try:
            summary = None
            n_files = self.get_steps(len(paths), params)
            for c, path in enumerate(paths, 1):
                zipfile = ZipFile(path)
                data_path = zipfile.extract()

                summary = MonthSummary(client)
                summary.add_files_in_folder(data_path)
                summary.save()

                if create_providers:
                    self.progress.emit((c * 2 - 1) / n_files)

                    summary.generate_providers()
                    self.progress.emit(c * 2 / n_files)
                else:
                    self.progress.emit(c / n_files)

            self.success.emit(summary, n_files)
        except Exception as error:
            self.error.emit(error)
            traceback.print_exc()


class QMonthSummary(AsyncExecutionMixin, BaseWidget):
    layout_class = QVBoxLayout
    margin = (5, 5, 5, 5)

    worker_class = MonthSummaryWorker

    def create_ui(self):
        self.selector = QFileSelector(self, filter="*.zip")
        self.prov_check = QCheckBox('Proveedores', self)

        self.metrics = QMetrics(self)
        self.execute_btn = QProgressButton('ejecutar', self, fn=self.start_worker)
        self.execute_btn.setProperty('class', 'primary')

    def load_ui(self, layout):
        layout.addItem(spacer)
        layout.addWidget(self.selector)
        layout.addWidget(self.prov_check)
        layout.addItem(spacer)

        layout.addWidget(self.metrics)
        layout.addWidget(self.execute_btn)

    def validate_data(self):
        client = getattr(self.parent(), 'client_selector').get_current()
        get_paths = self.selector.get_files()

        params = {
            'create_providers': self.prov_check.isChecked(),
        }

        return get_paths, client, params

    def start_worker(self):
        super().start_worker()
        self.execute_btn.setEnabled(False)

    def on_progress(self, progress):
        logger.info(f'MonthSummary, progress: {progress}')
        self.execute_btn.setProgress(progress)

    def on_success(self, summary, n_files):
        self.execute_btn.setEnabled(True)
        self.metrics.add_registers_today(n_files)
        self.selector.clear()

        title = '¿Desea abrirlo?'
        message = f'Se generó correctamente.\n{summary.filename}\n{title}'
        QConfirmMessageBox(self, message, summary.startfile, title=title)

    def on_error(self, error):
        self.execute_btn.setEnabled(True)

        raise QDialogException(self, str(error), format=False)
