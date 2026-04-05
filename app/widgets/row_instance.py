from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem


class QRowInstance:
    def __init__(self, table, fields):
        self.fields = fields
        self.table = table

    def create_row(self, instance):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.update_row(row, instance)

    def update_row(self, row, instance):
        for col, field in enumerate(self.fields):
            value = str(getattr(instance, field.name, None) or '')

            item = QTableWidgetItem(value)
            if col == 0:
                item.setData(Qt.ItemDataRole.UserRole, instance)

            self.table.setItem(row, col, item)
