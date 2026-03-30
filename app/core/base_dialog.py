from qframelesswindow import FramelessDialog

from app.mixin.loadui_mixin import LoadUiMixin
from app.mixin.window_mixin import WindowMixin


class BaseDialog(WindowMixin, LoadUiMixin, FramelessDialog):
    def __init__(self, *args, **kwargs):
        self.widget_class = kwargs.pop('widget', None)
        super().__init__(*args, **kwargs)

    def create_ui(self):
        self.widget = self.widget_class(self)

    def load_ui(self, layout):
        layout.addWidget(self.widget)
