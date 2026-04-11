from pathlib import Path

from PySide6.QtCore import QSettings as QBaseSettings

from app.settings import ORGANIZATION_NAME, APPLICATION_NAME, DEFAULT_WORK_DIR
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
        super().__init__(conf_format, scope, ORGANIZATION_NAME, f'{APPLICATION_NAME}\\conf')
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
        return Path(str(self.value('workdir', DEFAULT_WORK_DIR)))


settings = QSettings()

WORKDIR = settings.get_workdir()
