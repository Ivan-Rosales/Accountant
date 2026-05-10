from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTableWidget, QAbstractItemView, QTableWidgetItem

from app.mixin.model import ModelMixin
from app.widgets.row_instance import QRowInstance
from base.widget import BaseWidget


class QTableModel(ModelMixin, BaseWidget):
    start_signal = Signal()

    flex = {
        'id': 0.2,
    }

    def create_ui(self):
        self.table = QTableWidget(self)
        self.table.setColumnCount(len(self.fields))
        self.headers_labels = [(i.comment or i.name).capitalize() for i in self.fields]
        self.table.setHorizontalHeaderLabels(self.headers_labels)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.initial_resize = False

        self.row_instance = QRowInstance(self.table, self.fields)
        self.model.on_change(self.load_instances)

    def load_ui(self, layout):
        layout.addWidget(self.table)

    def filter_rows_by_text(self, text):
        def filter_func(instance):
            uuid_string = getattr(instance, '_uuid_string', None)

            if uuid_string is None:
                uuid_string = ' '.join([str(getattr(instance, i.name)) for i in self.fields])
                setattr(instance, '_uuid_string', uuid_string)

            return text.lower() in uuid_string.lower()

        self.filter_rows(filter_func)

    def filter_rows(self, filter_func):
        for row in range(self.table.rowCount()):
            instance = self.get_row_instance(row)
            self.table.setRowHidden(row, not filter_func(instance))

    def clear_filter(self):
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)

    def resize_columns(self):
        table_width = self.table.viewport().width() * 0.98
        flexs = [self.flex.get(col.lower(), 1) for col in self.headers_labels]
        count_flex = sum(flexs)

        width_per_unit = table_width // count_flex
        widths = [int(width_per_unit * col) for col in flexs]

        col = None
        for col, width in enumerate(widths):
            self.table.setColumnWidth(col, width)

        last_col_width = widths[col] + int(table_width - (width_per_unit * count_flex))
        self.table.setColumnWidth(col, last_col_width)

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

    def showEvent(self, event):
        if not self.initial_resize:
            self.resize_columns()
            self.initial_resize = True
        super().showEvent(event)
