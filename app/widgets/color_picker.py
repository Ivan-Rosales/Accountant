from functools import cached_property

from PySide6.QtWidgets import QRadioButton, QButtonGroup

from app.mixin.property_update import PropertyMixin
from base.widget import BaseWidget
from base.window import THEMES


class QThemePicker(PropertyMixin, BaseWidget):
    colors: list | dict = list(THEMES.keys())

    def create_ui(self):
        self.buttons = QButtonGroup()
        colors = self.colors.copy()
        self.colors = {}

        for color in colors:
            radio = QRadioButton(parent=self)
            self.buttons.addButton(radio)
            radio.setText(color.capitalize())

            self.colors[color.lower()] = radio

    def load_ui(self, layout):
        for widget in self.colors.values():
            layout.addWidget(widget)

    @cached_property
    def changeTheme(self):
        return self.buttons.buttonToggled

    def get_value(self):
        selected = self.buttons.checkedButton()
        if selected is None: return None
        return selected.text().lower()

    def set_value(self, theme):
        if not isinstance(self.colors, dict): return
        if radio := self.colors.get(theme):
            radio.setChecked(True)

    def setProperty(self, *args, **kwargs):
        for widget in self.colors.values():
            self.setPropertyUpddate(widget, *args, **kwargs)
