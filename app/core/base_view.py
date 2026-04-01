from pathlib import Path

from qframelesswindow import FramelessWindow

from app.mixin.loadui_mixin import LoadUiMixin
from app.mixin.window_mixin import WindowMixin
from settings import QSS_PATH


class BaseView(WindowMixin, LoadUiMixin, FramelessWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName(self.__class__.__name__)

        style_sheet = Path(QSS_PATH).read_text()
        self.setStyleSheet(style_sheet)
