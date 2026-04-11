from pathlib import Path

from PySide6.QtGui import QIcon
from qframelesswindow import FramelessWindow, StandardTitleBar

from app import settings as app_settings
from app.core.settings import settings
from app.mixin.loadui import LoadUiMixin
from app.mixin.property_update import PropertyMixin


class BaseWindow(PropertyMixin, LoadUiMixin, FramelessWindow):
    style_sheets = 'assets/qss/*.qss'
    icon_path = app_settings.ICON_PATH
    title = 'Contabilidad'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName(self.__class__.__name__)

        self.setTitleBar(StandardTitleBar(self))
        self.setWindowIcon(QIcon(self.icon_path))
        self.setWindowTitle(self.title.capitalize())

        self.load_qss()
        self._settings = settings

    def load_qss(self):
        self.setStyleSheet('')

        if isinstance(self.style_sheets, str):
            self.style_sheets = list(Path().glob(self.style_sheets))

        if isinstance(self.style_sheets, (list, tuple)):
            for style_sheet_path in self.style_sheets:
                file = Path(style_sheet_path)
                self.add_style_sheet(file.read_text())

        if app_settings.SHOW_BORDER:
            self.add_style_sheet('* { border: 1px solid red; }')

    def add_style_sheet(self, style_sheet):
        current_style_sheet = self.styleSheet()
        self.setStyleSheet(f'{current_style_sheet}\n{style_sheet}')

    def closeEvent(self, event):
        self._settings.set_widget_values()
        super().closeEvent(event)
