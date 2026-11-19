from functools import cached_property

from PySide6.QtWidgets import QComboBox

from app.mixin.property_update import PropertyMixin
from base.widget import BaseWidget


class QOptionSelector(PropertyMixin, BaseWidget):
    """Lista desplegable de opciones {valor: etiqueta} para la configuración."""
    windows_size = None
    options: dict = {}

    def __init__(self, *args, **kwargs):
        self.options = kwargs.pop('options', None) or self.options
        super().__init__(*args, **kwargs)

    def create_ui(self):
        self.combo = QComboBox(self)
        for value, label in self.options.items():
            self.combo.addItem(label, value)

    def load_ui(self, layout):
        layout.addWidget(self.combo)

    @cached_property
    def changeOption(self):
        return self.combo.currentIndexChanged

    def get_value(self):
        return self.combo.currentData()

    def set_value(self, value):
        index = self.combo.findData(value)
        if index >= 0: self.combo.setCurrentIndex(index)

    def setToolTip(self, text):
        self.combo.setToolTip(text)

    def setProperty(self, *args, **kwargs):
        self.setPropertyUpddate(self.combo, *args, **kwargs)
