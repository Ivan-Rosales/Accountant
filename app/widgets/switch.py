"""Interruptor (switch) para valores sí/no y combo que solo cambia con clic."""
from functools import cached_property

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, QRectF, QSize, Signal
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QAbstractButton, QComboBox, QLabel, QHBoxLayout

from app.mixin.property_update import PropertyMixin
from base.widget import BaseWidget


class QSwitch(QAbstractButton):
    """Interruptor animado. Usa el color del tema (lo fija la ventana al cargar el tema)."""
    accent = '#0d6efd'
    track_off = '#3d444d'
    knob = '#ffffff'

    def __init__(self, parent=None, checked=False):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._offset = 1.0 if checked else 0.0
        self._animation = QPropertyAnimation(self, b'offset', self)
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def sizeHint(self):
        return QSize(40, 22)

    def minimumSizeHint(self):
        return self.sizeHint()

    def getOffset(self):
        return self._offset

    def setOffset(self, value):
        self._offset = value
        self.update()

    offset = Property(float, getOffset, setOffset)  # noqa

    def _animate(self, checked):
        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def setChecked(self, checked):
        super().setChecked(checked)
        if not self.isVisible():  # sin animación al inicializar
            self._offset = 1.0 if checked else 0.0

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        rect = QRectF(0, 0, 40, 22).translated(0, (self.height() - 22) / 2)
        off, on = QColor(self.track_off), QColor(self.accent)
        t = self._offset
        track = QColor(int(off.red() + (on.red() - off.red()) * t), int(off.green() + (on.green() - off.green()) * t),
                       int(off.blue() + (on.blue() - off.blue()) * t))
        if not self.isEnabled(): track.setAlpha(110)
        painter.setBrush(track)
        painter.drawRoundedRect(rect, 11, 11)

        diameter = 16
        x = rect.left() + 3 + (rect.width() - diameter - 6) * t
        painter.setBrush(QColor(self.knob))
        painter.drawEllipse(QRectF(x, rect.top() + 3, diameter, diameter))
        painter.end()

    def hitButton(self, pos):
        return self.rect().contains(pos)


class QSwitchField(PropertyMixin, BaseWidget):
    """Interruptor con texto. Para la configuración guarda un valor distinto por estado (on/off)."""
    windows_size = None
    margin = (0, 4, 0, 4)
    spacing = 10
    toggled = Signal(bool)

    def __init__(self, *args, **kwargs):
        self.text = kwargs.pop('text', '')
        self.values = kwargs.pop('values', (True, False))  # (valor encendido, valor apagado)
        super().__init__(*args, **kwargs)

    def create_ui(self):
        self.switch = QSwitch(self)
        self.label = QLabel(self.text, self)
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.label.mousePressEvent = lambda _: self.switch.toggle()
        self.switch.toggled.connect(self.toggled.emit)

    def load_ui(self, layout: QHBoxLayout):
        layout.addWidget(self.switch)
        layout.addWidget(self.label, 1)

    @cached_property
    def changeOption(self):
        return self.switch.toggled

    def isChecked(self):
        return self.switch.isChecked()

    def setChecked(self, checked):
        self.switch.setChecked(bool(checked))

    def get_value(self):
        return self.values[0] if self.switch.isChecked() else self.values[1]

    def set_value(self, value):
        self.switch.setChecked(str(value) == str(self.values[0]))

    def setToolTip(self, text):
        self.switch.setToolTip(text)
        self.label.setToolTip(text)

    def setProperty(self, *args, **kwargs):
        self.setPropertyUpddate(self.label, *args, **kwargs)


class QClickComboBox(QComboBox):
    """Combo que no cambia de opción con la rueda del mouse (solo con clic o teclado)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        event.ignore()  # la rueda desplaza la página en lugar de cambiar el valor
