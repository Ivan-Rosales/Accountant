from functools import cached_property
from pathlib import Path

from PySide6.QtCore import Qt, QEvent, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QPainter, QIcon
from PySide6.QtWidgets import QPushButton, QSpacerItem, QSizePolicy

spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


class QButton(QPushButton):
    def __init__(self, description, parent=None, **kwargs):
        self.icon_opacity = self.safe_opacity(kwargs.pop('icon_opacity', 1))
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
            disabled_opacity = self.safe_opacity(self.icon_opacity - 0.8, min_value=0.1)
            painter.setOpacity(self.icon_opacity if self.isEnabled() else disabled_opacity)
            painter.drawPixmap(0, 0, pixmap)
        self.setIcon(QIcon(result))

    def set_opacity_icon(self, opacity):
        self.icon_opacity = self.safe_opacity(opacity)
        self.set_special_button()

    def safe_opacity(self, opacity, max_value=1.0, min_value=0.0):
        return max(min_value, min(opacity, max_value))

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

    def darken_color(self, hex_color, factor=0.5):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = int(r * (1 - factor))
        g = int(g * (1 - factor))
        b = int(b * (1 - factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    @cached_property
    def bg_color(self):
        return self.palette().button().color().name()

    @cached_property
    def bg_secondary(self):
        return self.darken_color(self.bg_color)

    def getProgress(self):
        return self._progress

    def setProgressValue(self, value):
        value = max(0.0, min(1.0, value))
        if value == self._progress: return

        self._progress = value
        self.updateProgress()

    progress = Property(float, getProgress, setProgressValue)  # noqa

    def resetProgress(self):
        self.setProgress(1)

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
                                stop:{stop} {self.bg_secondary}, 
                                stop:1 {self.bg_secondary}
                            );
            '''

        self.setStyleSheet(style_sheet)
