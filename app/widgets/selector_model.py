from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QSizePolicy

from app.core.base_dialog import BaseDialog
from app.core.base_widget import BaseWidget
from app.mixin.model_mixin import ModelMixin
from app.widgets.common import QButton
from app.widgets.table_form_model import QTableFormModel


class QSelectorModel(ModelMixin, BaseWidget):
    def create_ui(self):
        self.list = QComboBox(self)
        self.list.setCursor(Qt.CursorShape.PointingHandCursor)

        self.admin_btn = QButton('assets/icons/gear-icon.png', self, fn=self.show_dialog)
        self.admin_btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self.model.connect_func(self.load_instances)

    def load_ui(self, layout):
        layout.addWidget(self.list)
        layout.addWidget(self.admin_btn)

    def show_dialog(self):
        title = f'administración de {self.model.__name__}s'
        dialog = BaseDialog(self, widget=QTableFormModel, title=title)
        dialog.show()

    def get_current(self):
        return self.list.currentData()

    def load_instances(self, instances):
        self.list.clear()

        for instance in instances:
            self.list.addItem(str(instance), instance)
