from pathlib import Path

from qframelesswindow import FramelessWindow

from app import settings as app_settings
from app.core.settings import settings
from app.mixin.loadui import LoadUiMixin
from app.mixin.property_update import PropertyMixin
from app.mixin.title_bar import TitleBarMixin
from app.settings import DEFAULT_THEME, QSS_PATH
from logger import logger

THEMES = {
    'azul': ('#0d6efd', '#0b5ed7', '#0a58ca', '#0a53be'),
    'verde': ('#20c997', '#1aa179', '#178f6b', '#136f54'),
    'rojo': ('#F87575', '#FA8080', '#FF8E8E', '#FFA1A1'),
    'morado': ('#6f42c1', '#5a32a3', '#4e2a91', '#41247a'),
    'naranja': ('#fd7e14', '#e66f0e', '#cc610c', '#b4530a'),
}


class BaseWindow(TitleBarMixin, PropertyMixin, LoadUiMixin, FramelessWindow):
    style_sheets = QSS_PATH
    _load_qs = True

    def __init__(self, *args, **kwargs):
        self.themes = THEMES
        super().__init__(*args, **kwargs)
        self.setObjectName(self.__class__.__name__)

        if self._load_qs: self.load_qss()

        self._settings = settings

    def load_qss(self, theme=None):
        self.theme = theme or settings.value('theme')
        if self.theme not in self.themes:
            logger.warning(f'Theme {self.theme} not found.')
            settings.setValue('theme', DEFAULT_THEME)
            self.theme = DEFAULT_THEME

        color = self.themes[self.theme]
        self.setStyleSheet('')

        primary = color[0]
        self.setWindowIcon(self.svg_to_icon(self.icon_path, color=primary))

        logger.info(f'Set application theme {self.theme}')

        if isinstance(self.style_sheets, str):
            path = Path(self.style_sheets)
            self.style_sheets = list(path.parent.glob(path.name))

        if isinstance(self.style_sheets, (list, tuple)):
            for style_sheet_path in self.style_sheets:
                file = Path(style_sheet_path)
                self.add_style_sheet(file.read_text(), color)

        if app_settings.SHOW_BORDER:
            self.add_style_sheet('* { border: 1px solid red; }', color)

    def add_style_sheet(self, style_sheet, color):
        current_style_sheet = self.styleSheet()
        labels = ('{{color}}', '{{hover}}', '{{border}}', '{{pressed}}')

        for i, label in enumerate(labels):
            style_sheet = style_sheet.replace(label, color[i])

        self.setStyleSheet(f'{current_style_sheet}\n{style_sheet}')

    def closeEvent(self, event):
        self._settings.set_widget_values()
        super().closeEvent(event)
