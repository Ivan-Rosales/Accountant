from PySide6.QtGui import QIcon
from qframelesswindow import StandardTitleBar

from settings import ICON_PATH


class WindowMixin:
    icon_path = ICON_PATH
    title = 'Contabilidad'
    margin = (10, 42, 10, 10)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setTitleBar(StandardTitleBar(self))
        self.setWindowIcon(QIcon(self.icon_path))
        self.setWindowTitle(self.title.capitalize())
