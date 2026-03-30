from PySide6.QtWidgets import QTableWidget

from app.core.base_widget import BaseWidget
from app.mixin.model_mixin import ModelMixin


class QTableModel(ModelMixin, BaseWidget):
    def create_ui(self):
        fields = self.get_fields()

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(fields))
        self.table.setHorizontalHeaderLabels(list(fields.keys()))

    def load_ui(self, layout):
        layout.addWidget(self.table)
