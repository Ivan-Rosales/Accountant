from PySide6.QtWidgets import QGridLayout, QLabel

from app.settings import BASE_PATH, ICON_PATH, QSS_PATH, SHOW_PATHS
from app.widgets.common import QButton
from base.widget import BaseWidget


class QDebugTools(BaseWidget):
    layout_class = QGridLayout

    def create_ui(self):
        self.qss_btn = QButton('recargar qss', self, fn=self.reload_qss)

        if SHOW_PATHS:
            self.base_path = QLabel(f'Base path - {BASE_PATH}', self)
            self.icon_path = QLabel(f'Icon path - {ICON_PATH}', self)
            self.qss_path = QLabel(f'QSS path - {QSS_PATH}', self)

    def load_ui(self, layout: QGridLayout):
        layout.addWidget(self.qss_btn, 0, 0)

        if SHOW_PATHS:
            layout.addWidget(self.base_path, 1, 0)
            layout.addWidget(self.icon_path, 2, 0)
            layout.addWidget(self.qss_path, 3, 0)

    def reload_qss(self):
        parent = self.parent()

        while parent is not None:
            if hasattr(parent, 'load_qss'):
                parent.load_qss()
                break

            parent = parent.parent()
