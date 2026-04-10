from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


class QSecondaryLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        self.setProperty('class', 'secondary')
        self.setStyleSheet('padding: 1px')

        font = self.font()
        font.setBold(True)
        self.setFont(font)
