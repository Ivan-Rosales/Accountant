from PySide6.QtWidgets import QTableWidget, QVBoxLayout, QPushButton, QTableWidgetItem, QLabel
from qframelesswindow import FramelessDialog

from app.core.base_widget import BaseWidget
from app.mixin.database_mixin import DatabaseMixin

"""
data = {
    'name': 'test',
    'last_name': 'test',
    'rfc': 'test',
}

self.execute_db(lambda: self.model.create(**data), {'success': self.on_create})
"""


class QModelInstanceDialog(FramelessDialog):
    def create_ui(self):
        self.create_btn = QLabel('crear', self)

    def load_ui(self, layout):
        layout.addWidget(self.create_btn)
        layout.addWidget(self.update_btn)
        layout.addWidget(self.delete_btn)


class QTableController(BaseWidget):
    def create_ui(self):
        parent = self.parent()

        self.create_btn = QPushButton('crear', self)
        self.create_btn.clicked.connect(parent.create_fun)

        self.update_btn = QPushButton('modificar', self)
        self.update_btn.clicked.connect(parent.update_fun)

        self.delete_btn = QPushButton('eliminar', self)
        self.delete_btn.clicked.connect(parent.delete_fun)

    def load_ui(self, layout):
        layout.addWidget(self.create_btn)
        layout.addWidget(self.update_btn)
        layout.addWidget(self.delete_btn)


class QTableModel(DatabaseMixin, BaseWidget):
    layout_class = QVBoxLayout
    _fields = None

    def __init__(self, model, parent=None):
        self.model = model
        super().__init__(parent)

        self.execute_db(self.model.all, {'success': self.on_success})

    @property
    def fields(self):
        if self._fields is None:
            meta = getattr(self.model, '_meta')
            self._fields = meta.fields_map

        return self._fields

    def create_ui(self):
        self.controllers = QTableController(self)
        self.model_dialog = QModelInstanceDialog

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.fields))
        self.table.setHorizontalHeaderLabels(list(self.fields.keys()))

    def load_ui(self, layout):
        layout.addWidget(self.controllers)
        layout.addWidget(self.table)

    def on_success(self, queryset):
        if not isinstance(queryset, list): return

        for instance in queryset:
            row = self.table.rowCount()

            self.table.insertRow(row)
            for col, field in enumerate(self.fields):
                data = getattr(instance, field) or ''
                self.table.setItem(row, col, QTableWidgetItem(str(data)))

    def create_fun(self):
        dialog = self.model_dialog(self)
        dialog.show()

    def update_fun(self):
        dialog = self.model_dialog(self)
        dialog.show()

    def delete_fun(self):
        print('delete_fun', self)
