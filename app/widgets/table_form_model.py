from PySide6.QtCore import Signal
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
    list_changed = Signal()

    def create_ui(self):
        self.controllers = QTableFormModelControllers(self)

        self.table = QTableModel(self)
        self.table.table.itemSelectionChanged.connect(self.on_select)

    def load_ui(self, layout):
        layout.addWidget(self.controllers)
        layout.addWidget(self.table)
        self.on_select()

    def on_select(self):
        selection = self.table.get_selection()
        self.controllers.update_btn.setEnabled(len(selection) == 1)
        self.controllers.delete_btn.setEnabled(len(selection) > 0)

    def create_fn(self):
        dialog = BaseDialog(self, widget=QFormModel)
        dialog.widget.save.connect(self.on_save)
        dialog.show()

    def update_fn(self):
        select = self.table.get_selection()[0]
        row = select.row()
        instance = self.table.get_row_instance(row)

        dialog = BaseDialog(self, widget=QFormModel)
        dialog.widget.save.connect(self.on_save)
        dialog.widget.set_instance(instance)
        dialog.show()

    def delete_fn(self):
        self.table.delete_selection()
        self.list_changed.emit()

    def on_save(self, data):
        is_new, instance = data

        if is_new:
            self.table.create_row(instance)
        else:
            row = self.table.get_selection()[0].row()
            self.table.update_row(row, instance)

        self.list_changed.emit()
