from datetime import datetime

from PySide6.QtCore import Qt
from qframelesswindow import FramelessDialog

from app.mixin.loadui import LoadUiMixin
from app.mixin.title_bar import TitleBarMixin

open_dialogs = {}


class BaseDialog(TitleBarMixin, LoadUiMixin, FramelessDialog):
    margin = (24, 48, 24, 20)
    windows_size = (440, 200)

    def __init__(self, *args, **kwargs):
        self.uuid = kwargs.pop('uuid', str(datetime.now().timestamp()))
        self.title = kwargs.pop('title', self.title)
        self.widget_class = kwargs.pop('widget', None)
        super().__init__(*args, **kwargs)
        self.setObjectName(self.__class__.__name__)
        # Modal estándar: solo botón de cerrar y tamaño fijo
        for name in ('minBtn', 'maxBtn'):
            if button := getattr(self.titleBar, name, None):
                button.hide()
        if hasattr(self, 'setResizeEnabled'): self.setResizeEnabled(False)
        self.titleBar.setDoubleClickEnabled(False) if hasattr(self.titleBar, 'setDoubleClickEnabled') else None
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

    def create_ui(self):
        self.widget = self.widget_class(self)

    def load_ui(self, layout):
        layout.addWidget(self.widget)

    def show(self):
        is_open = open_dialogs.get(self.uuid, False)
        if is_open: return

        open_dialogs[self.uuid] = True
        super().show()

    def showEvent(self, event):
        super().showEvent(event)
        from app.widgets.animations import window_fade_in
        window_fade_in(self)

    def hide(self):
        super().hide()
        open_dialogs[self.uuid] = False

    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)
        open_dialogs[self.uuid] = False
