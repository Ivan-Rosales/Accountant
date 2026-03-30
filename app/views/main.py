from PySide6.QtCore import QThread

from app.core.base_view import BaseView
from app.core.db_worker import DatabaseWorker
from app.models.client import Client
from app.widgets.selector_model import QSelectorModel


class MainView(BaseView):
    def __init__(self, *args, **kwargs):
        self.db_thread = QThread()
        self.db_worker = DatabaseWorker()
        self.db_worker.moveToThread(self.db_thread)
        self.db_thread.start()

        super().__init__(*args, **kwargs)

    def create_ui(self):
        self.client_selector = QSelectorModel(self, context={'model': Client})

    def load_ui(self, layout):
        layout.addWidget(self.client_selector)
