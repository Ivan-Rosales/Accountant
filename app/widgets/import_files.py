from pathlib import Path

from PySide6.QtWidgets import QVBoxLayout, QFileDialog, QSizePolicy, QMessageBox

from app.mixin.async_execution import AsyncExecutionMixin
from app.widgets.common import QProgressButton
from app.widgets.message_dialog import QMessageDialog
from app.workers.import_files import ImportFilesWorker
from base.widget import BaseWidget
from exceptions import ValidationException
from models import Cliente


class QImportWidget(AsyncExecutionMixin, BaseWidget):
    layout_class = QVBoxLayout

    worker_class = ImportFilesWorker

    def create_ui(self):
        self.clients = {}
        self.default_label = 'importar archivos'.capitalize()
        self.execute_btn = QProgressButton(self.default_label, self, fn=self.select_path)
        self.execute_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        Cliente.on_change(self.set_clients)

    def load_ui(self, layout):
        layout.addWidget(self.execute_btn)

    def set_clients(self, clients):
        self.clients = {i.rfc: i for i in clients}

    def select_path(self):
        self.files = []

        path_str = QFileDialog.getExistingDirectory()
        if path_str is None: return
        path = Path(path_str)
        if not path.is_dir(): return

        self.base_path = path
        self.start_worker()

    def validate_data(self):
        if self.base_path is None:
            raise ValidationException('Base path not set')

        return self.base_path, self.clients

    def start_worker(self):
        super().start_worker()
        self.execute_btn.setText('buscando archivos...'.capitalize())

    def on_progress(self, progress, *args):
        total = args[0]
        super().on_progress(progress)
        self.execute_btn.setText(f'{int(progress * total)}/{total} archivos')

        try:
            file = args[1]
            self.execute_btn.setText(f'{int(progress * total)}/{total} archivos\n{file}')
        except:
            pass

    def on_success(self, summary):
        self.execute_btn.setText(self.default_label)
        self.execute_btn.setEnabled(True)
        self.execute_btn.resetProgress()

        success_files = {key: value for key, value in summary.items() if value[0]}
        error_files = {key: value for key, value in summary.items() if not value[0]}

        message = QMessageDialog(self)
        message.setIcon(QMessageBox.Icon.Information)
        message.setText('\n'.join([
            f'{len(summary)} Archivos procesados',
            f'{len(success_files)} Archivos importados',
            f'{len(error_files)} Archivos con error',
        ]))

        detailed_text = '\n'.join([f'-- {file}\n{desc[1]}\n\n' for file, desc in error_files.items()])
        message.setDetailedText(detailed_text)

        message.exec()
