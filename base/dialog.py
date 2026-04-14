from datetime import datetime

from qframelesswindow import FramelessDialog

from app.mixin.loadui import LoadUiMixin
from app.mixin.title_bar import TitleBarMixin

open_dialogs = {}


class BaseDialog(TitleBarMixin, LoadUiMixin, FramelessDialog):
    margin = (10, 42, 10, 10)

    def __init__(self, *args, **kwargs):
        self.uuid = kwargs.pop('uuid', str(datetime.now().timestamp()))
        self.title = kwargs.pop('title', self.title)
        self.widget_class = kwargs.pop('widget', None)
        super().__init__(*args, **kwargs)
        self.setObjectName(self.__class__.__name__)

    def create_ui(self):
        self.widget = self.widget_class(self)

    def load_ui(self, layout):
        layout.addWidget(self.widget)

    def show(self):
        is_open = open_dialogs.get(self.uuid, False)
        if is_open: return

        open_dialogs[self.uuid] = True
        super().show()

    def hide(self):
        super().hide()
        open_dialogs[self.uuid] = False

    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)
        open_dialogs[self.uuid] = False
