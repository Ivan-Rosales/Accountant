from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QAbstractItemView, QTableWidgetItem, QHeaderView

from app.core.base_widget import BaseWidget
from app.mixin.model_mixin import ModelMixin
from app.widgets.row_instance import QRowInstance


class QTableModel(ModelMixin, BaseWidget):
    def create_ui(self):
        self.table = QTableWidget(self)
        self.table.setColumnCount(len(self.fields))
        self.table.setHorizontalHeaderLabels([(i.comment or i.name).capitalize() for i in self.fields])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setVisible(False)

        self.row_instance = QRowInstance(self.table, self.fields)
        self.model.connect_func(self.load_instances)

    def load_ui(self, layout):
        layout.addWidget(self.table)

    def load_instances(self, instances):
        self.table.setRowCount(0)

        for instance in instances:
            self.create_row(instance)

    def get_selection(self):
        return self.table.selectionModel().selectedRows()

    def get_row_instance(self, row):
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def create_row(self, instance):
        self.row_instance.create_row(instance)

    def delete_selection(self):
        selection = self.get_selection()
        for select in selection:
            row = select.row()
            row_item: QTableWidgetItem = self.table.item(row, 0)
            instance = row_item.data(Qt.ItemDataRole.UserRole)
            self.model.delete(instance)
