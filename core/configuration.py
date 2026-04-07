from PySide6.QtCore import QSettings

from core.logger import logger
from settings import ORGANIZATION_NAME, APPLICATION_NAME


class Settings(QSettings):
    _instance = None
    _initialized = False

    widgets: dict = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self.__class__._initialized: return
        scope = QSettings.Scope.UserScope
        conf_format = QSettings.Format.IniFormat
        super().__init__(conf_format, scope, ORGANIZATION_NAME, f'{APPLICATION_NAME}\\conf')
        logger.info(f'Configuration file {self.fileName()}')
        self.__class__._initialized = True

    def register_setting(self, key, getter, setter, default=None):
        self.widgets[key] = (getter, setter)
        value = self.value(key) or default
        if value: setter(value)

    def get_widget_values(self):
        for key, (getter, setter) in self.widgets.items():
            self.setValue(key, getter())
