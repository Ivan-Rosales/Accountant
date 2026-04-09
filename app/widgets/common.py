from functools import cached_property
from pathlib import Path

from PySide6.QtCore import Qt, QEvent, Property, QPropertyAnimation, QEasingCurve
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


class QProgressButton(QButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._progress = 1.0
        self._anim = None
        self._easing = QEasingCurve.Type.OutCubic
        self._duration = 300

    @cached_property
    def bg_color(self):
        return self.palette().button().color().name()

    def getProgress(self):
        return self._progress

    def setProgressValue(self, value):
        value = max(0.0, min(1.0, value))
        if value == self._progress: return

        self._progress = value
        self.updateProgress()

    progress = Property(float, getProgress, setProgressValue)  # noqa

    def setProgress(self, value):
        value = max(0.0, min(1.0, value))

        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setDuration(self._duration)
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(value)
        self._anim.setEasingCurve(self._easing)

        self._anim.start()

    def updateProgress(self):
        color = self.bg_color
        stop = self._progress
        stop_prev = max(0.0, stop - 0.002)

        style_sheet = '' if stop == 1 else f'''
                background: qlineargradient(
                                x1:0, y1:0, x2:1, y2:0, 
                                stop:0 {color}, 
                                stop:{stop_prev} {color}, 
                                stop:{stop} transparent, 
                                stop:1 transparent
                            );
            '''

        self.setStyleSheet(style_sheet)
