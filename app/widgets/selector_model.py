from PySide6.QtWidgets import QComboBox

from app.core.base_dialog import BaseDialog
from app.core.base_widget import BaseWidget
from app.widgets.common import QButton
from app.widgets.table_form_model import QTableFormModel


class QSelectorModel(BaseWidget):
    def create_ui(self):
        self.list = QComboBox(self)
        self.admin_btn = QButton("admin", self, fn=self.show_dialog)

    def load_ui(self, layout):
        layout.addWidget(self.list)
        layout.addWidget(self.admin_btn)

    def show_dialog(self):
        dialog = BaseDialog(self, widget=QTableFormModel)
        dialog.show()
