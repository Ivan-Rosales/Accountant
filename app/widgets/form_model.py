from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QLabel, QLineEdit
from sqlalchemy.sql.sqltypes import String

from app.core.base_widget import BaseWidget
from app.mixin.model_mixin import ModelMixin
from app.widgets.common import QButton, spacer

FIELDS_MAPPING = {
    String: QLineEdit,
}


class QFormModel(ModelMixin, BaseWidget):
    layout_class = QVBoxLayout
    save = Signal(object)
    id = None

    def create_ui(self):
        self.widgets = {}

        for name, field in self.fields.items():
            if name in ['id']: continue

            field_class = type(field.type)
            field_form = FIELDS_MAPPING[field_class]
            self.widgets[name] = field_form()

        self.save_btn = QButton('Guardar', self, fn=self.on_save)
        self.save_btn.setProperty('class', 'primary')

    def load_ui(self, layout):
        for name, field in self.widgets.items():
            label = QLabel(name.capitalize())

            layout.addWidget(label)
            layout.addWidget(field)

        layout.addItem(spacer)
        layout.addWidget(self.save_btn)

    def get_data(self):
        data = {'id': self.id}
        for name, field in self.widgets.items():
            data[name] = field.text()

        return data

    def set_instance(self, instance):
        self.id = instance.id
        for name, field in self.widgets.items():
            value = str(getattr(instance, name, None) or '')
            field.setText(value)

    def on_save(self):
        data = self.get_data()

        pk = data.get('id', None)
        is_new = pk is None

        if is_new:
            self.model.create(**data)
        else:
            self.model.update(**data)

        self.parent().hide()
