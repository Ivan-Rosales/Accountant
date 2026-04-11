from pathlib import Path

from PySide6.QtCore import QSettings as QBaseSettings

from app import settings as base_settings
from logger import logger


class QSettings(QBaseSettings):
    _instance = None
    _initialized = False

    widgets: dict = {}

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

    def register_setting(self, key, getter, setter, default=None):
        self.widgets[key] = (getter, setter)
        value = self.value(key) or default
        if value: setter(value)

    def set_widget_values(self):
        for key, (getter, setter) in self.widgets.items():
            self.setValue(key, getter())

    def get_workdir(self):
        return Path(str(self.value('workdir', base_settings.DEFAULT_WORK_DIR)))

    def get_database_dir(self):
        return Path(str(self.value('database_dir', base_settings.DEFAULT_DATABASE_DIR)))


settings = QSettings()

WORKDIR = settings.get_workdir()
DATABASE_DIR = settings.get_database_dir()
