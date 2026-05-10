from PySide6.QtWidgets import QVBoxLayout, QLabel, QSizePolicy, QHBoxLayout, QLineEdit

from app.mixin.model import ModelMixin
from app.mixin.property_update import PropertyMixin
from app.widgets.common import QButton
from app.widgets.form_model import QFormModel
from app.widgets.table_model import QTableModel
from base.dialog import BaseDialog
from base.widget import BaseWidget
from functions import get_icon


class QTableFormModelControllers(ModelMixin, BaseWidget, PropertyMixin):
    margin = (3, 0, 7, 0)
    spacing = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName("TableControllers")

    def search_toggle(self):
        set_visible = not self.line_edit.isVisible()
        self.setPropertyUpddate(self.search_btn, 'open', 'true' if set_visible else 'false')
        self.line_edit.setVisible(set_visible)
        if set_visible:
            self.line_edit.setFocus()
        else:
            self.line_edit.clear()

    def create_ui(self):
        parent = self.parent()
        model_name = self.model.__name__

        self.label = QLabel(model_name, self)

        self.line_edit = QLineEdit(self)
        self.line_edit.textChanged.connect(parent.table.filter_rows_by_text)
        self.line_edit.hide()

        self.search_btn = QButton(get_icon('search'), self, fn=self.search_toggle)
        self.search_btn.setProperty('position', 'first')
        self.search_btn.setToolTip('Buscar...')

        self.reset_btn = QButton(get_icon('column'), self, fn=parent.table.resize_columns)
        self.reset_btn.setProperty('position', 'middle')
        self.reset_btn.setToolTip('Reiniciar ancho de columnas')

        self.create_btn = QButton(get_icon('plus'), self, fn=parent.create_fn)
        self.create_btn.setProperty('position', 'middle')
        self.create_btn.setToolTip(f'Añadir {model_name}')

        self.update_btn = QButton(get_icon('pencil'), self, fn=parent.update_fn)
        self.update_btn.setProperty('position', 'middle')
        self.update_btn.setToolTip(f'Actualizar {model_name}')

        self.delete_btn = QButton(get_icon('trash'), self, fn=parent.delete_fn)
        self.delete_btn.setProperty('position', 'last')
        self.delete_btn.setToolTip(f'Borrar {model_name}')

    def load_ui(self, layout: QHBoxLayout):
        layout.addWidget(self.label, 10)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.search_btn)

        layout.addWidget(self.reset_btn)
        layout.addWidget(self.create_btn)
        layout.addWidget(self.update_btn)
        layout.addWidget(self.delete_btn)


class QTableFormModel(ModelMixin, BaseWidget):
    layout_class = QVBoxLayout
    spacing = 0

    def create_ui(self):
        self.table = QTableModel(self)
        self.controllers = QTableFormModelControllers(self)
        self.table.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.table.table.itemSelectionChanged.connect(self.on_select)
        self.table.table.doubleClicked.connect(self.update_fn)

    def load_ui(self, layout):
        layout.addWidget(self.controllers)
        layout.addWidget(self.table)
        self.on_select()

    def on_select(self):
        selection = self.table.get_selection()
        self.controllers.update_btn.setEnabled(len(selection) == 1)
        if del_en := len(selection) > 0:
            self.controllers.delete_btn.setToolTip(f'Borrar {self.model.__name__} ({len(selection)})')
        self.controllers.delete_btn.setEnabled(del_en)

    def create_fn(self):
        uuid = f'{self.model.__name__}_create'
        title = f'crear {self.model.__name__.capitalize()}'
        dialog = BaseDialog(self, widget=QFormModel, title=title, uuid=uuid)
        dialog.show()

    def update_fn(self, index=None):
        if index:
            row = index.row()
        else:
            select = self.table.get_selection()[0]
            row = select.row()

        instance = self.table.get_row_instance(row)

        uuid = f'{self.model.__name__}_update'
        title = f'actualizar {self.model.__name__.capitalize()} {instance}'
        dialog = BaseDialog(self, widget=QFormModel, title=title, uuid=uuid)
        dialog.widget.set_instance(instance)
        dialog.show()

    def delete_fn(self):
        self.table.delete_selection()
