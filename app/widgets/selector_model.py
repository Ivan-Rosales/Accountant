from PySide6.QtWidgets import QComboBox

from app.core.base_dialog import BaseDialog
from app.core.base_widget import BaseWidget
from app.mixin.database_mixin import DatabaseMixin
from app.mixin.model_mixin import ModelMixin
from app.widgets.common import QButton
from app.widgets.table_form_model import QTableFormModel


class QSelectorModel(ModelMixin, DatabaseMixin, BaseWidget):
    def create_ui(self):
        self.list = QComboBox(self)
        self.admin_btn = QButton("admin", self, fn=self.show_dialog)
        self.list_changed()

    def load_ui(self, layout):
        layout.addWidget(self.list)
        layout.addWidget(self.admin_btn)

    def show_dialog(self):
        dialog = BaseDialog(self, widget=QTableFormModel)
        dialog.widget.list_changed.connect(self.list_changed)
        dialog.show()

    def get_current(self):
        return self.list.currentData()

    def list_changed(self):
        model = self.get_model()
        self.execute_db(model.all, {'success': self.on_load})

    def on_load(self, instances):
        self.list.clear()

        for instance in instances:
            self.list.addItem(str(instance), instance)
