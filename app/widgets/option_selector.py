from functools import cached_property


from app.mixin.property_update import PropertyMixin
from app.widgets.switch import QClickComboBox
from base.widget import BaseWidget


class QOptionSelector(PropertyMixin, BaseWidget):
    """Lista desplegable de opciones {valor: etiqueta} para la configuración."""
    windows_size = None
    options: dict = {}

    def __init__(self, *args, **kwargs):
        self.options = kwargs.pop('options', None) or self.options
        super().__init__(*args, **kwargs)

    def create_ui(self):
        self.combo = QClickComboBox(self)
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


class QTextField(PropertyMixin, BaseWidget):
    """Campo de texto para la configuración. Con `secret=True` oculta lo escrito (contraseñas)."""
    windows_size = None

    def __init__(self, *args, **kwargs):
        self.secret = kwargs.pop('secret', False)
        self.placeholder = kwargs.pop('placeholder', '')
        super().__init__(*args, **kwargs)

    def create_ui(self):
        from PySide6.QtWidgets import QLineEdit
        self.input = QLineEdit(self)
        self.input.setPlaceholderText(self.placeholder)
        if self.secret:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)

    def load_ui(self, layout):
        layout.addWidget(self.input)

    @cached_property
    def changeOption(self):
        return self.input.textEdited

    def get_value(self):
        return self.input.text().strip()

    def set_value(self, value):
        self.input.setText('' if value is None else str(value))

    def setPlaceholderText(self, text):
        self.input.setPlaceholderText(text)

    def setToolTip(self, text):
        self.input.setToolTip(text)

    def setProperty(self, *args, **kwargs):
        self.setPropertyUpddate(self.input, *args, **kwargs)
