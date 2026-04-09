from pathlib import Path

from qframelesswindow import FramelessWindow

import settings
from app.core.settings import QSettings
from app.mixin.loadui import LoadUiMixin
from app.mixin.property_update import PropertyMixin


class BaseWindow(PropertyMixin, LoadUiMixin, FramelessWindow):
    style_sheets = 'assets/qss/*.qss'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName(self.__class__.__name__)

        self.load_qss()
        self.app_settings = QSettings()

    def load_qss(self):
        self.setStyleSheet('')

        if isinstance(self.style_sheets, str):
            self.style_sheets = list(Path().glob(self.style_sheets))

        if isinstance(self.style_sheets, (list, tuple)):
            for style_sheet_path in self.style_sheets:
                file = Path(style_sheet_path)
                self.add_style_sheet(file.read_text())

        if settings.DEBUG:
            self.add_style_sheet('* { border: 1px solid red; }')

    def add_style_sheet(self, style_sheet):
        current_style_sheet = self.styleSheet()
        self.setStyleSheet(f'{current_style_sheet}\n{style_sheet}')

    def closeEvent(self, event):
        self.app_settings.get_widget_values()
        super().closeEvent(event)
