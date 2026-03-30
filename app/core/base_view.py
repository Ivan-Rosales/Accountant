from qframelesswindow import FramelessWindow

from app.mixin.loadui_mixin import LoadUiMixin
from app.mixin.window_mixin import WindowMixin


class BaseView(WindowMixin, LoadUiMixin, FramelessWindow):
    pass
