from PySide6.QtWidgets import QVBoxLayout

from app.core.base_dialog import BaseDialog
from app.core.base_widget import BaseWidget
from app.widgets.common import QButton
from app.widgets.form_model import QFormModel
from app.widgets.table_model import QTableModel


class QTableFormModelControllers(BaseWidget):
    def create_ui(self):
        parent = self.parent()

        self.create_btn = QButton('+', self, fn=parent.create_fn)
        self.update_btn = QButton('x', self, fn=parent.update_fn)
        self.delete_btn = QButton('-', self, fn=parent.delete_fn)

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

    def create_fn(self):
        dialog = BaseDialog(self, widget=QFormModel)
        dialog.show()

    def update_fn(self):
        dialog = BaseDialog(self, widget=QFormModel)
        dialog.show()

    def delete_fn(self):
        pass
