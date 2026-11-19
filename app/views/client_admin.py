from app.widgets.table_form_model import QTableFormModel
from base.tab import TabWidget
from models import Cliente


class QClientAdmin(TabWidget):
    tooltip_label = 'administrar clientes'
    page_title = 'Clientes'
    page_subtitle = 'Alta, edición y baja de los contribuyentes que lleva'

    def create_ui(self):
        self.table_form = QTableFormModel(self, context={'model': Cliente})

    def load_ui(self, layout):
        layout.addWidget(self.table_form)
