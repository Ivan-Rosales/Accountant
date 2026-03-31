from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QAbstractItemView, QTableWidgetItem

from app.core.base_widget import BaseWidget
from app.mixin.database_mixin import DatabaseMixin
from app.mixin.model_mixin import ModelMixin
from app.widgets.row_instance import QRowInstance


class QTableModel(ModelMixin, DatabaseMixin, BaseWidget):
    def create_ui(self):
        model = self.get_model()
        fields = self.get_fields()

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(fields))
        self.table.setHorizontalHeaderLabels(list(fields.keys()))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        self.row_instance = QRowInstance(self.table, fields)

        self.execute_db(model.all, {'success': self.on_load})

    def load_ui(self, layout):
        layout.addWidget(self.table)

    def get_selection(self):
        return self.table.selectionModel().selectedRows()

    def get_row_instance(self, row):
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def create_row(self, instance):
        self.row_instance.create_row(instance)

    def update_row(self, row, instance):
        self.row_instance.update_row(row, instance)

    def delete_selection(self):
        async def delete_selection_inner():
            await model.filter(id__in=pks).delete()
            return rows

        model = self.get_model()

        pks = []
        rows = []
        selection = self.get_selection()
        for select in selection:
            row = select.row()
            row_item: QTableWidgetItem = self.table.item(row, 0)
            instance = row_item.data(Qt.ItemDataRole.UserRole)
            pks.append(instance.pk)
            rows.append(row)

        self.execute_db(delete_selection_inner, {'success': self.on_delete})

    def on_load(self, instances):
        for instance in instances:
            self.create_row(instance)

    def on_delete(self, rows):
        for row in rows:
            self.table.removeRow(row)

        self.table.clearSelection()
