from pathlib import Path

import toml
from PySide6.QtCore import QSettings as QBaseSettings

from app import settings as base_settings
from logger import logger

config = toml.load('pyproject.toml')


class QSettings(QBaseSettings):
    _instance = None
    _initialized = False

    widgets: dict = {}

    defaults = {
        'theme': base_settings.DEFAULT_THEME,
        'workdir': base_settings.DEFAULT_WORK_DIR,
        'dbdir': base_settings.DEFAULT_DATABASE_DIR,
    }

    version = config['project']['version']

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(QBaseSettings, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self.__class__._initialized: return
        scope = QBaseSettings.Scope.UserScope
        conf_format = QBaseSettings.Format.IniFormat
        super().__init__(conf_format, scope, base_settings.ORGANIZATION_NAME, f'{base_settings.APPLICATION_NAME}\\conf')
        self.__class__._initialized = True

        logger.info(f'Configuration file {self.fileName()}')

    def value(self, key, default=None):
        default = default or self.defaults.get(key)
        return super().value(key, default)

    def register_setting(self, key, getter, setter, default=None):
        self.widgets[key] = (getter, setter)
        value = self.value(key, default)
        if value: setter(value)

        logger.debug(f'Registered widget {key}')

    def set_widget_values(self):
        for key, (getter, setter) in self.widgets.items():
            value = getter()
            self.setValue(key, value)

            logger.debug(f'Register saved widget {key} {value}')

    def get_workdir(self):
        return Path(str(self.value('workdir')))


settings = QSettings()
