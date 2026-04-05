from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout

import settings
from app.core.base_popup import QDialogException
from app.core.base_view import BaseView
from app.messages_box.confirm_box import QConfirmMessageBox
from app.widgets.common import QButton, spacer
from app.widgets.debug_tools import QDebugTools
from app.widgets.file_selector import QFileSelector
from app.widgets.metrics import QMetrics
from app.widgets.selector_model import QSelectorModel
from core.database import database_worker
from core.exceptions import ValidationException
from core.models import Cliente
from core.month_summary import MonthSummary
from core.zip_file import ZipFile


class MainView(BaseView):
    layout_class = QVBoxLayout
    size = (700, 300)

    def __init__(self, *args, **kwargs):
        self.db_thread = QThread()
        self.db_worker = database_worker
        self.db_worker.moveToThread(self.db_thread)
        self.db_thread.start()

        super().__init__(*args, **kwargs)

    def create_ui(self):
        self.debug_tools = QDebugTools(self)

        self.client_selector = QSelectorModel(self, context={'model': Cliente})
        self.selector = QFileSelector(self, filter="*.zip")

        self.metrics = QMetrics(self)

        self.footer = QHBoxLayout()
        self.execute_btn = QButton('ejecutar', self, fn=self.execute)
        self.execute_btn.setProperty('class', 'primary')
        self.footer.addWidget(self.execute_btn)

    def load_ui(self, layout):
        if settings.DEBUG:
            layout.addWidget(self.debug_tools)

        layout.addWidget(self.client_selector)
        layout.addWidget(self.selector)

        layout.addItem(spacer)

        layout.addWidget(self.metrics)
        layout.addItem(self.footer)

    def execute(self):
        self.execute_btn.setDisabled(True)

        try:
            raw_paths = self.selector.get_files()
            paths = [Path(i) for i in raw_paths]
            client = self.client_selector.get_current()

            n_files = len(paths)
            for path in paths:
                zipfile = ZipFile(path)
                data_path = zipfile.extract()

                summary = MonthSummary(client)
                summary.add_files_in_folder(data_path)
                summary.save()

                if n_files == 1:
                    message = f'Se generó correctamente.\n{summary.path}\n¿Desea abrirlo?'
                    QConfirmMessageBox(self, message, summary.startfile)

            self.metrics.add_registers_today(n_files)
        except ValidationException as error:
            raise QDialogException(self, str(error), format=False)
        finally:
            self.execute_btn.setEnabled(True)
