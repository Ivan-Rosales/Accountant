from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QLabel, QSpacerItem, QSizePolicy
from tortoise.fields.data import TextField

from app.core.base_widget import BaseWidget
from app.mixin.database_mixin import DatabaseMixin
from app.mixin.model_mixin import ModelMixin
from app.widgets.common import QButton

FIELDS_MAPPING = {
    TextField: QLineEdit,
}


class QFormModel(ModelMixin, DatabaseMixin, BaseWidget):
    layout_class = QVBoxLayout
    save = Signal(object)
    id = None

    def create_ui(self):
        self.widgets = {}

        fields = self.get_fields()

        for name, field in fields.items():
            if name in ['id']: continue

            field_class = type(field)
            field_form = FIELDS_MAPPING[field_class]
            self.widgets[name] = field_form()

        self.spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.save_btn = QButton('Guardar', self, fn=self.on_save)

    def load_ui(self, layout):
        for name, field in self.widgets.items():
            label = QLabel(name)

            layout.addWidget(label)
            layout.addWidget(field)

        layout.addItem(self.spacer)
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
        async def on_insert():
            instance = await model.create(**data)
            return is_new, instance

        async def on_update():
            await model.filter(pk=pk).update(**data)
            instance = await model.get(pk=pk)
            return is_new, instance

        data = self.get_data()
        model = self.get_model()

        pk = data.pop('id', None)
        is_new = pk is None

        if is_new:
            self.execute_db(on_insert, {'success': self.save.emit})
        else:
            self.execute_db(on_update, {'success': self.save.emit})

        self.parent().hide()
