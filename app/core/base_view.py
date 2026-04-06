from pathlib import Path

from qframelesswindow import FramelessWindow

import settings
from app.mixin.loadui_mixin import LoadUiMixin
from app.mixin.window_mixin import WindowMixin
from core.configuration import Settings


class BaseView(WindowMixin, LoadUiMixin, FramelessWindow):
    style_sheets = 'assets/qss/*.qss'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName(self.__class__.__name__)

        self.load_qss()

        self.settings = Settings()

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

    def setPropertyUpddate(self, widget, key, value):
        widget.setProperty(key, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def closeEvent(self, event):
        self.settings.get_widget_values()
        super().closeEvent(event)
