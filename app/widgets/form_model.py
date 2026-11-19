from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QHBoxLayout
from sqlalchemy.sql.sqltypes import String

from app.mixin.model import ModelMixin
from app.widgets.common import QButton
from app.widgets.table_model import label_for
from base.widget import BaseWidget

FIELDS_MAPPING = {
    String: QLineEdit,
}


class QFormModel(ModelMixin, BaseWidget):
    """Formulario de alta/edición dentro de un modal estándar: campos con etiqueta y Cancelar/Guardar."""
    layout_class = QVBoxLayout
    windows_size = None
    spacing = 6
    save = Signal(object)
    id = None

    def create_ui(self):
        self.widgets = {}
        self.labels = {}

        for name, field in self.fields.items():
            if name in ['id']: continue

            field_class = type(field.type)
            widget = FIELDS_MAPPING[field_class](self)
            label = label_for(field)
            widget.setPlaceholderText(label)
            if name == 'rfc':
                widget.setMaxLength(13)
                widget.textEdited.connect(lambda text, w=widget: w.setText(text.upper()))
            widget.returnPressed.connect(self.on_save)
            self.widgets[name] = widget
            self.labels[name] = label

        self.error = QLabel(self)
        self.error.setProperty('class', 'invalid')
        self.error.hide()

        self.cancel_btn = QButton('cancelar', self, fn=lambda: self.parent().hide())
        self.save_btn = QButton('guardar', self, fn=self.on_save)
        self.save_btn.setProperty('class', 'primary')
        self.save_btn.setDefault(True)

    def load_ui(self, layout):
        for name, field in self.widgets.items():
            label = QLabel(self.labels[name], self)
            label.setProperty('class', 'field-label')
            layout.addWidget(label)
            layout.addWidget(field)

        layout.addWidget(self.error)
        layout.addSpacing(10)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.save_btn)
        layout.addLayout(buttons)

        if self.widgets:
            next(iter(self.widgets.values())).setFocus(Qt.FocusReason.OtherFocusReason)

    def get_data(self):
        data = {'id': self.id}
        for name, field in self.widgets.items():
            data[name] = field.text().strip()

        return data

    def set_instance(self, instance):
        self.id = instance.id
        for name, field in self.widgets.items():
            value = str(getattr(instance, name, None) or '')
            field.setText(value)

    def validate(self, data):
        if 'rfc' in data and len(data['rfc']) not in (12, 13):
            return 'El RFC debe tener 12 (persona moral) o 13 (persona física) caracteres'
        return None

    def on_save(self):
        data = self.get_data()
        if message := self.validate(data):
            self.error.setText(message)
            self.error.show()
            return

        pk = data.get('id', None)
        is_new = pk is None

        if is_new:
            self.model.create(**data)
        else:
            self.model.update(**data)

        self.parent().hide()
