from pathlib import Path

import toml
from PySide6.QtCore import QSettings as QBaseSettings

from app import settings as base_settings
from app.settings import TOML_PATH
from logger import logger

config = toml.load(TOML_PATH)


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

    def register_setting(self, key, getter, setter, default=None, signal=None):
        """Recuerda el estado de un widget entre sesiones.

        Si el valor guardado no se puede aplicar (borrado, de otra versión, corrupto) se usa `default`
        en silencio; si tampoco se puede, el widget se queda como está. Con `signal`, el estado se
        guarda en cuanto cambia (no solo al cerrar), para no perderlo si la app se cierra mal.
        """
        self.widgets[key] = (getter, setter)
        try:
            value = self.value(key, default)
        except Exception as error:
            logger.debug(f'Cached widget {key} could not be read: {error}')
            value = default

        for candidate in (value, default):
            if not candidate: continue
            try:
                setter(candidate)
                break
            except Exception as error:
                logger.debug(f'Cached widget {key}={candidate!r} could not be applied: {error}')

        if signal is not None:
            signal.connect(lambda *_: self.save_widget_value(key))

        logger.debug(f'Registered widget {key}')

    def save_widget_value(self, key):
        getter, _ = self.widgets.get(key, (None, None))
        if getter is None: return
        try:
            self.setValue(key, getter())
        except Exception as error:
            logger.debug(f'Widget {key} could not be cached: {error}')

    def set_widget_values(self):
        for key in list(self.widgets):
            self.save_widget_value(key)

    def get_workdir(self):
        return Path(str(self.value('workdir')))


settings = QSettings()
