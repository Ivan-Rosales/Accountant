from pathlib import Path

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPixmap, QPainter, QIcon
from PySide6.QtWidgets import QPushButton, QSpacerItem, QSizePolicy

spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


class QButton(QPushButton):
    def __init__(self, description, parent=None, **kwargs):
        fn = kwargs.pop('fn', None)
        super().__init__('', parent, **kwargs)
        if callable(fn): self.clicked.connect(fn)
        self.description = description
        self.set_special_button()

    def set_special_button(self):
        path = Path(self.description)

        if not path.is_file():
            self.setText(self.description.capitalize())
            return

        pixmap = QPixmap(path)
        result = QPixmap(pixmap.size())
        result.fill(Qt.GlobalColor.transparent)
        with QPainter(result) as painter:
            painter.setOpacity(1 if self.isEnabled() else 0.2)
            painter.drawPixmap(0, 0, pixmap)
        self.setIcon(QIcon(result))

    def changeEvent(self, event):
        if event.type() == QEvent.Type.EnabledChange:
            self.set_special_button()
        super().changeEvent(event)
