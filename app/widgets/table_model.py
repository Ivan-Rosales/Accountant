from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from app.core.base_widget import BaseWidget
from app.mixin.database_mixin import DatabaseMixin
from app.mixin.model_mixin import ModelMixin


class QTableModel(ModelMixin, DatabaseMixin, BaseWidget):
    def create_ui(self):
        model = self.get_model()
        fields = self.get_fields()

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(fields))
        self.table.setHorizontalHeaderLabels(list(fields.keys()))

        self.execute_db(model.all, {'success': self.on_success})

    def load_ui(self, layout):
        layout.addWidget(self.table)

    def on_success(self, clients):
        fields = self.get_fields()

        for client in clients:
            row = self.table.rowCount()
            self.table.insertRow(row)

            for col, field in enumerate(fields):
                value = str(getattr(client, field) or '')
                self.table.setItem(row, col, QTableWidgetItem(value))
