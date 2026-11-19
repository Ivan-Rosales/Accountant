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
    'azul': ('#0d6efd', '#0b5ed7', '#0a58ca', '#0a53be', '#fff'),
    'verde': ('#20c997', '#1aa179', '#178f6b', '#136f54', '#fff'),
    'rojo': ('#F87575', '#FA8080', '#FF8E8E', '#FFA1A1', '#fff'),
    'morado': ('#6f42c1', '#5a32a3', '#4e2a91', '#41247a', '#fff'),
    'naranja': ('#fd7e14', '#e66f0e', '#cc610c', '#b4530a', '#fff'),
    'gris': ('#6c757d', '#5c636a', '#4F575C', '#4c555d', '#fff'),
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

        primary = color[0]
        from app.widgets.switch import QSwitch
        QSwitch.accent = primary
        for switch in self.findChildren(QSwitch):
            switch.update()
        self.setWindowIcon(self.svg_to_icon(self.icon_path, color=primary))

        logger.info(f'Set application theme {self.theme}')

        if isinstance(self.style_sheets, str):
            path = Path(self.style_sheets)
            self.style_sheets = list(path.parent.glob(path.name))

        # Un solo setStyleSheet: aplicar cada archivo por separado recalculaba el estilo de toda la ventana N veces
        sheets = [Path(path).read_text(encoding='utf-8') for path in self.style_sheets]
        if app_settings.SHOW_BORDER:
            sheets.append('* { border: 1px solid red; }')
        self.setStyleSheet(self.render_style_sheet('\n'.join(sheets), color))

    @staticmethod
    def render_style_sheet(style_sheet, color):
        labels = ('{{color}}', '{{hover}}', '{{border}}', '{{pressed}}', '{{text}}')
        for i, label in enumerate(labels):
            style_sheet = style_sheet.replace(label, color[i])
        return style_sheet

    def add_style_sheet(self, style_sheet, color):
        self.setStyleSheet(f'{self.styleSheet()}\n{self.render_style_sheet(style_sheet, color)}')

    def closeEvent(self, event):
        self._settings.set_widget_values()
        super().closeEvent(event)
