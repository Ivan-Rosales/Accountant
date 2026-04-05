from PySide6.QtWidgets import QVBoxLayout

from app.core.base_widget import BaseWidget
from app.widgets.common import QButton


class QDebugTools(BaseWidget):
    layout = QVBoxLayout()

    def create_ui(self):
        self.qss_btn = QButton('recargar qss', self, fn=self.reload_qss)

    def load_ui(self, layout):
        layout.addWidget(self.qss_btn)

    def reload_qss(self):
        parent = self.parent()

        while parent is not None:
            if hasattr(parent, 'load_qss'):
                parent.load_qss()
                break

            parent = parent.parent()
