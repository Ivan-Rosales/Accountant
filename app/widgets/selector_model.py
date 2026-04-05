from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox

from app.core.base_widget import BaseWidget
from app.mixin.model_mixin import ModelMixin


class QSelectorModel(ModelMixin, BaseWidget):
    def create_ui(self):
        self.list = QComboBox(self)
        self.list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.model.connect_func(self.load_instances)

        # self.admin_btn = QButton(get_icon('gear'), self, fn=self.show_dialog)
        # self.admin_btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)

    def load_ui(self, layout):
        layout.addWidget(self.list)

    def get_current(self):
        return self.list.currentData()

    def load_instances(self, instances):
        self.list.clear()

        for instance in instances:
            self.list.addItem(str(instance), instance)
