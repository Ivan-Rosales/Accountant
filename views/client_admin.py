from app.core.base_widget import BaseWidget
from app.widgets.table_form_model import QTableFormModel
from core.models import Cliente


class QClientAdmin(BaseWidget):
    margin = (5, 5, 5, 5)

    def create_ui(self):
        self.table_form = QTableFormModel(self, context={'model': Cliente})

    def load_ui(self, layout):
        layout.addWidget(self.table_form)
