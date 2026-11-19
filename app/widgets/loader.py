"""Indicador de carga que cubre un widget mientras corre una tarea."""
from PySide6.QtCore import Qt, QTimer, QEvent, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget

from app.widgets.switch import QSwitch


class QLoadingOverlay(QWidget):
    """Capa semitransparente con un spinner y un mensaje sobre `target`.

    Aparece con un pequeño retraso para no parpadear en operaciones rápidas y bloquea los clics
    sobre el widget cubierto mientras está visible.
    """
    SHOW_DELAY_MS = 150

    def __init__(self, target: QWidget):
        super().__init__(target)
        self.target = target
        self.message = ''
        self.angle = 0
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.hide()

        self.spin_timer = QTimer(self)
        self.spin_timer.setInterval(16)
        self.spin_timer.timeout.connect(self._spin)

        self.delay_timer = QTimer(self)
        self.delay_timer.setSingleShot(True)
        self.delay_timer.timeout.connect(self._show_now)

        target.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.target and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.setGeometry(self.target.rect())
        return False

    def start(self, message=''):
        self.message = message
        self.update()
        if not self.isVisible() and not self.delay_timer.isActive():
            self.delay_timer.start(self.SHOW_DELAY_MS)

    def stop(self):
        self.delay_timer.stop()
        self.spin_timer.stop()
        self.hide()

    @property
    def active(self):
        return self.isVisible() or self.delay_timer.isActive()

    def _show_now(self):
        self.setGeometry(self.target.rect())
        self.raise_()
        self.show()
        self.spin_timer.start()

    def _spin(self):
        self.angle = (self.angle + 6) % 360
        self.update()

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(22, 25, 29, 190))

        size = 34
        center_y = self.height() / 2 - (12 if self.message else 0)
        rect = QRectF(self.width() / 2 - size / 2, center_y - size / 2, size, size)

        pen = QPen(QColor('#30363d'), 4)
        painter.setPen(pen)
        painter.drawEllipse(rect)
        pen.setColor(QColor(QSwitch.accent))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, -self.angle * 16, 100 * 16)

        if self.message:
            font = QFont(self.font())
            font.setPointSize(10)
            painter.setFont(font)
            painter.setPen(QColor('#c9d1d9'))
            text_rect = QRectF(0, rect.bottom() + 10, self.width(), 24)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self.message)
        painter.end()

    def mousePressEvent(self, event):
        event.accept()  # bloquea clics mientras carga
