from PySide6.QtWidgets import QPushButton

from app.widgets.table_model import QTableModel
from app.core.base_dialog import BaseDialog
from app.core.base_widget import BaseWidget
from app.models.client import Client


class QClientsDialog(BaseDialog):
    title = "Clientes"

    def create_ui(self):
        self.clients_table = QTableModel(Client, self)

    def load_ui(self, layout):
        layout.addWidget(self.clients_table)


class QClientsAdmin(BaseWidget):
    def create_ui(self):
        self.show_btn = QPushButton("admin", self)
        self.show_btn.clicked.connect(self.show_fun)

        self.clients_dialog = QClientsDialog

    def load_ui(self, layout):
        layout.addWidget(self.show_btn)

    def show_fun(self):
        dialog = self.clients_dialog(self)
        dialog.show()
