from PySide6.QtWidgets import QLabel

from app.core.base_widget import BaseWidget


class QMetrics(BaseWidget):
    def create_ui(self):
        self.counter = QLabel('test', self)

    def load_ui(self, layout):
        layout.addWidget(self.counter)
