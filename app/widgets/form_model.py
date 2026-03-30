from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QLabel
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

    def create_ui(self):
        self.widgets = {}

        fields = self.get_fields()

        for name, field in fields.items():
            if name in ['id']: continue

            field_class = type(field)
            field_form = FIELDS_MAPPING[field_class]
            self.widgets[name] = field_form()

        self.save_btn = QButton('Guardar', self, fn=self.on_save)

    def load_ui(self, layout):
        for name, field in self.widgets.items():
            label = QLabel(name)

            layout.addWidget(label)
            layout.addWidget(field)

        layout.addWidget(self.save_btn)

    def get_data(self):
        data = {}
        for name, field in self.widgets.items():
            data[name] = field.text()

        return data

    def on_save(self):
        data = self.get_data()
        model = self.get_model()
        self.execute_db(lambda: model.create(**data))
