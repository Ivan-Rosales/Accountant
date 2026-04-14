import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from qframelesswindow import StandardTitleBar

from app import settings as app_settings


class TitleBarMixin:
    title = 'Contabilidad'
    icon_path = app_settings.ICON_PATH

    _theme = None
    _themes = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setTitleBar(StandardTitleBar(self))
        self.setWindowIcon(self.svg_to_icon(self.icon_path))
        self.setWindowTitle(self.title.capitalize())

    @property
    def theme(self):
        return TitleBarMixin._theme

    @theme.setter
    def theme(self, value):
        TitleBarMixin._theme = value

    @property
    def themes(self):
        return TitleBarMixin._themes

    @themes.setter
    def themes(self, value):
        TitleBarMixin._themes = value

    def svg_to_icon(self, path, color=None, size=32):
        if color is None and self.theme in self.themes:
            color = self.themes[self.theme][0]

        with open(path, "r", encoding="utf-8") as f:
            svg = f.read()

        def add_fill(match):
            tag = match.group(0)
            if 'fill=' in tag: return tag
            return tag.replace('<path', f'<path fill="{color}"')

        svg = re.sub(r'<path[^>]*>', add_fill, svg)

        renderer = QSvgRenderer(bytearray(svg, encoding="utf-8"))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)
