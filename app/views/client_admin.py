from app.widgets.table_form_model import QTableFormModel
from base.widget import BaseWidget
from models import Cliente


class QClientAdmin(BaseWidget):
    margin = (5, 5, 5, 5)

    def create_ui(self):
        self.table_form = QTableFormModel(self, context={'model': Cliente})

    def load_ui(self, layout):
        layout.addWidget(self.table_form)
