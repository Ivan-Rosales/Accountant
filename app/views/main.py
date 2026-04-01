from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QComboBox

from app.components.metrics import QMetrics
from app.core.base_view import BaseView
from app.core.db_worker import DatabaseWorker
from app.models.client import Client
from app.widgets.common import QButton
from app.widgets.file_selector import QFileSelector
from app.widgets.selector_model import QSelectorModel
from core.month_summary import MonthSummary
from core.zip_file import ZipFile


class MainView(BaseView):
    layout_class = QVBoxLayout

    def __init__(self, *args, **kwargs):
        self.db_thread = QThread()
        self.db_worker = DatabaseWorker()
        self.db_worker.moveToThread(self.db_thread)
        self.db_thread.start()

        super().__init__(*args, **kwargs)

    def create_ui(self):
        self.client_selector = QSelectorModel(self, context={'model': Client})
        self.selector = QFileSelector(self, filter="*.zip")

        self.metrics = QMetrics(self)

        self.footer = QHBoxLayout()
        self.execute_btn = QButton('ejecutar', self, fn=self.execute)
        self.footer.addWidget(self.execute_btn)

    def load_ui(self, layout):
        layout.addWidget(self.client_selector)
        layout.addWidget(self.selector)

        layout.addWidget(self.metrics)
        layout.addItem(self.footer)

    def execute(self):
        raw_paths = self.selector.get_files()
        paths = [Path(i) for i in raw_paths]
        client = self.client_selector.get_current()

        for path in paths:
            zipfile = ZipFile(path)
            data_path = zipfile.extract()

            summary = MonthSummary(client)
            summary.add_files_in_folder(data_path)
            summary.save()
