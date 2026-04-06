from PySide6.QtCore import QSettings, QCoreApplication


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
        conf_format = QSettings.Format.IniFormat
        scope = QSettings.Scope.UserScope
        application_name = QCoreApplication.applicationName()
        organization_name = QCoreApplication.organizationName()
        super().__init__(conf_format, scope, organization_name, application_name)
        self.__class__._initialized = True

    def register_setting(self, key, getter, setter, default=None):
        self.widgets[key] = (getter, setter)
        value = self.value(key) or default
        if value: setter(value)

    def get_widget_values(self):
        for key, (getter, setter) in self.widgets.items():
            self.setValue(key, getter())
