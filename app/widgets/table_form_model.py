from PySide6.QtWidgets import QVBoxLayout

from app.core.base_widget import BaseWidget
from app.widgets.common import QButton
from app.widgets.table_model import QTableModel


class QTableFormModelControllers(BaseWidget):
    def create_ui(self):
        self.create_btn = QButton('+', self)
        self.update_btn = QButton('x', self)
        self.delete_btn = QButton('-', self)

    def load_ui(self, layout):
        layout.addWidget(self.create_btn)
        layout.addWidget(self.update_btn)
        layout.addWidget(self.delete_btn)


class QTableFormModel(BaseWidget):
    layout_class = QVBoxLayout

    def create_ui(self):
        self.controllers = QTableFormModelControllers(self)
        self.table = QTableModel(self)

    def load_ui(self, layout):
        layout.addWidget(self.controllers)
        layout.addWidget(self.table)
