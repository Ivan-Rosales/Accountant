from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLineEdit, QSizePolicy

from app.mixin.model import ModelMixin
from app.widgets.common import QButton
from app.widgets.confirm_box import confirm_delete
from app.widgets.form_model import QFormModel
from app.widgets.table_model import QTableModel
from base.dialog import BaseDialog
from base.widget import BaseWidget
from functions import get_icon


class QTableFormModel(ModelMixin, BaseWidget):
    """Tabla con barra de acciones (buscar, nuevo, editar, eliminar) con el diseño del resto de pestañas."""
    layout_class = QVBoxLayout
    windows_size = None
    spacing = 12

    @property
    def model_label(self):
        return getattr(self.model, 'verbose_name', self.model.__name__.lower())

    def create_ui(self):
        self.table = QTableModel(self)
        self.table.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.table.table.itemSelectionChanged.connect(self.on_select)
        self.table.table.doubleClicked.connect(self.update_fn)

        self.search = QLineEdit(self)
        self.search.setPlaceholderText(f'Buscar {self.model_label} por nombre o RFC...')
        self.search.setClearButtonEnabled(True)
        self.search.addAction(get_qicon('search'), QLineEdit.ActionPosition.LeadingPosition)
        self.search.textChanged.connect(self.table.filter_rows_by_text)

        self.create_btn = QButton(f'nuevo {self.model_label}', self, fn=self.create_fn)
        self.create_btn.setProperty('class', 'primary')
        self.update_btn = QButton('editar', self, fn=self.update_fn)
        self.delete_btn = QButton('eliminar', self, fn=self.delete_fn)

    def load_ui(self, layout):
        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(self.update_btn)
        top.addWidget(self.delete_btn)
        top.addWidget(self.create_btn)
        layout.addLayout(top)
        layout.addWidget(self.table, 1)
        self.on_select()

    def on_select(self):
        selection = self.table.get_selection()
        self.update_btn.setEnabled(len(selection) == 1)
        self.delete_btn.setEnabled(len(selection) > 0)
        self.delete_btn.setText(f'Eliminar ({len(selection)})' if len(selection) > 1 else 'Eliminar')

    def create_fn(self):
        uuid = f'{self.model.__name__}_create'
        dialog = BaseDialog(self, widget=QFormModel, title=f'Nuevo {self.model_label}', uuid=uuid)
        dialog.show()

    def update_fn(self, index=None):
        if index:
            row = index.row()
        else:
            selection = self.table.get_selection()
            if len(selection) != 1: return
            row = selection[0].row()

        instance = self.table.get_row_instance(row)

        uuid = f'{self.model.__name__}_update'
        dialog = BaseDialog(self, widget=QFormModel, title=f'Editar {self.model_label}', uuid=uuid)
        dialog.widget.set_instance(instance)
        dialog.show()

    def delete_fn(self):
        rows = [index.row() for index in self.table.get_selection()]
        instances = [self.table.get_row_instance(row) for row in rows]
        if not instances: return
        detail = 'Los concentrados en Excel ya generados no se borran de la carpeta de trabajo.'
        if confirm_delete(self, [str(i) for i in instances], what=self.model_label, detail=detail):
            self.table.delete_selection()


def get_qicon(name):
    from PySide6.QtGui import QIcon
    return QIcon(get_icon(name))
