from functools import cached_property

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QGridLayout, QLabel

from app.core.settings import settings
from app.settings import DEFAULT_THEME, DEFAULT_WORK_DIR, DEFAULT_DATABASE_DIR
from app.widgets.color_picker import QThemePicker
from app.widgets.common import QButton, spacer
from app.widgets.file_selector import QDirSelector
from base.widget import BaseWidget
from functions import get_icon
from logger import logger


class QConfiguration(BaseWidget):
    change_configuration = Signal(str, object)
    layout_class = QGridLayout
    margin = (5, 5, 5, 5)
    touched = {}

    fields = {
        'theme': {
            'label': 'tema',
            'widget': QThemePicker,
            'default': DEFAULT_THEME,
        },
        'workdir': {
            'label': 'ruta de trabajo',
            'widget': QDirSelector,
            'default': DEFAULT_WORK_DIR,
        },
        'dbdir': {
            'label': 'ruta de base de datos',
            'widget': QDirSelector,
            'default': DEFAULT_DATABASE_DIR,
        }
    }

    @cached_property
    def widgets(self):
        return {label: desc['widget'] for label, desc in self.fields.items() if desc.get('widget')}

    def create_ui(self):
        for label, description in self.fields.items():
            widget_class = description.get('widget')
            widget = widget_class(self) if widget_class else None
            self.fields[label]['widget'] = widget
            self.set_value(widget, settings.value(label))
            self.set_on_change(label, widget)

        self.widgets['dbdir'].with_file('db.sqlite3')

        self.label = QLabel('hay cambios sin guardar'.capitalize(), self)
        self.label.setProperty('class', 'invalid')
        self.label.hide()

        self.save_btn = QButton('guardar'.capitalize(), self, fn=self.save_configuration)
        self.save_btn.setProperty('class', 'primary')

        self.reset_btn = QButton(get_icon('recurring'), self, fn=self.reset_configuration, icon_opacity=0.5)
        self.reset_btn.setProperty('type', 'flat')

    def load_ui(self, layout: QGridLayout):
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)

        fields_layout = QVBoxLayout()
        for label, description in self.fields.items():
            field_label = description.get('label', label)
            fields_layout.addWidget(QLabel(field_label.capitalize(), self))

            widget = description['widget']
            fields_layout.addWidget(widget)
        fields_layout.addItem(spacer)

        layout.addLayout(fields_layout, 0, 0, 1, 2)
        layout.addWidget(self.label, 1, 0, 1, 2)
        layout.addWidget(self.save_btn, 2, 0)
        layout.addWidget(self.reset_btn, 2, 1)

    def on_change(self, label, value):
        self.touched[label] = value

        widget = self.widgets[label]
        widget.setProperty('class', 'invalid')
        self.label.show()

    def get_value(self, widget):
        logger.debug(f'Getting configuration {widget.__class__.__name__}')

        if isinstance(widget, QDirSelector):
            return str(widget.get_path())
        elif isinstance(widget, QThemePicker):
            return widget.get_value()

        logger.warning(f'{self.__class__.__name__} is not defined get_value for {widget.__class__.__name__}')
        return None

    def set_value(self, widget, value):
        logger.debug(f'Setting configuration {widget.__class__.__name__} with value {value}')

        if isinstance(widget, QDirSelector):
            widget.setPlaceholderText(value)
            widget.setPath(value)
        elif isinstance(widget, QThemePicker):
            widget.set_value(value)
        else:
            logger.warning(f'{self.__class__.__name__} is not defined set_value for {widget.__class__.__name__}')

    def set_on_change(self, label, widget):
        if isinstance(widget, QDirSelector):
            widget.changeDir.connect(lambda *args, l=label, **kwargs: self.on_change(l, self.get_value(widget)))
        elif isinstance(widget, QThemePicker):
            widget.changeTheme.connect(lambda *args, l=label, **kwargs: self.on_change(l, self.get_value(widget)))
        else:
            logger.warning(f'{self.__class__.__name__} is not defined set_on_change for {widget.__class__.__name__}')

    def reset_configuration(self):
        for label, description in self.fields.items():
            widget = description.get('widget')
            default_value = description.get('default')
            self.set_value(widget, default_value)

        logger.info(f'{self.__class__.__name__} reset configuration to default')

    def save_configuration(self):
        for label, value in self.touched.items():
            settings.setValue(label, value)
            logger.debug(f'Change configuration {label} to {value}')
            self.change_configuration.emit(label, value)

            widget = self.widgets[label]
            widget.setProperty('class', None)
            self.label.hide()

        logger.debug(f'Configuration saved')

    def get_conf_value(self, label):
        return self.get_value(self.widgets[label])

    def register_change(self, register, function):
        def wrapper(label, *args, **kwargs):
            if register == label: return function(*args, **kwargs)
            return None

        self.change_configuration.connect(wrapper)
