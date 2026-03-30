from PySide6.QtWidgets import QComboBox

from app.widgets.clients_admin import QClientsAdmin
from app.core.base_widget import BaseWidget


class QClientsSelector(BaseWidget):
    def create_ui(self):
        self.clients = QComboBox(self)
        self.clients_admin = QClientsAdmin(self)

    def load_ui(self, layout):
        layout.addWidget(self.clients)
        layout.addWidget(self.clients_admin)
