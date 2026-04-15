from functools import cached_property

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QLabel

from app.core.settings import settings
from app.settings import DEFAULT_THEME, DEFAULT_WORK_DIR, DEFAULT_DATABASE_DIR
from app.widgets.color_picker import QThemePicker
from app.widgets.common import spacer, QButton
from app.widgets.file_selector import QDirSelector
from base.widget import BaseWidget
from functions import get_icon
from logger import logger


class QConfiguration(BaseWidget):
    change_configuration = Signal(str, object)
    layout_class = QVBoxLayout
    margin = (5, 5, 5, 5)
    last = None

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
            self.set_on_change(label, widget)

            self.fields[label]['widget'] = widget
            settings.register_setting(
                label,
                lambda w=widget: self.get_value(w),
                lambda value, w=widget: self.set_value(w, value),
            )

        self.widgets['dbdir'].with_file('db.sqlite3')
        self.reset_btn = QButton(get_icon('recurring'), self, fn=self.reset_configuration, icon_opacity=0.5)
        self.reset_btn.setText('Restablecer configuración'.capitalize())

    def load_ui(self, layout):
        for label, description in self.fields.items():
            field_label = description.get('label', label)
            layout.addWidget(QLabel(field_label.capitalize(), self))

            widget = description['widget']
            layout.addWidget(widget)
        layout.addItem(spacer)

        layout.addWidget(self.reset_btn)

    def register_change(self, register, function):
        def wrapper(label, *args, **kwargs):
            if register == label: return function(*args, **kwargs)
            return None

        self.change_configuration.connect(wrapper)

    def on_change(self, label, value):
        if self.last == (label, value): return
        logger.debug(f'Change configuration {label} to {value}')

        settings.setValue(label, value)
        self.change_configuration.emit(label, value)
        self.last = (label, value)

    def get_conf_value(self, label):
        return self.get_value(self.widgets[label])

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
