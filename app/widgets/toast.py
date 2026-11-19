"""Notificaciones flotantes (toasts) en la esquina superior derecha, bajo el encabezado.

    toast(self, 'Concentrado regenerado', detail=str(path), action=('Abrir', summary.startfile))

Entran deslizándose, se apilan, se cierran solas (la duración se pausa con el mouse encima) y pueden
tener un botón de acción. Para errores se siguen usando modales.
"""
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QPoint, QEvent
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QGraphicsOpacityEffect, QWidget

from app.widgets.message_dialog import QModalIcon, KIND_SUCCESS

MARGIN, GAP, WIDTH = 18, 10, 360
TOP_OFFSET = 92  # debajo de la barra de título y del selector de cliente (no tapa botones de acción)


class QToast(QFrame):
    def __init__(self, manager, text, detail='', kind=KIND_SUCCESS, action=None, duration=4500):
        super().__init__(manager.window)
        self.manager = manager
        self.setProperty('class', 'toast')
        self.setFixedWidth(WIDTH)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 10, 12)
        layout.setSpacing(12)

        icon = QModalIcon(self, kind, size=30)
        layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        title = QLabel(text, self)
        title.setProperty('class', 'toast-title')
        title.setWordWrap(True)
        texts.addWidget(title)
        if detail:
            body = QLabel(detail, self)
            body.setProperty('class', 'secondary')
            body.setWordWrap(True)
            texts.addWidget(body)
        layout.addLayout(texts, 1)

        if action is not None:
            label, fn = action
            button = QPushButton(label, self)
            button.setProperty('class', 'primary')
            button.clicked.connect(lambda: (fn(), self.dismiss()))
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)

        close = QPushButton('✕', self)
        close.setProperty('type', 'flat')
        close.setFixedSize(26, 26)
        close.setToolTip('Cerrar')
        close.clicked.connect(self.dismiss)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(duration)
        self.timer.timeout.connect(self.dismiss)
        self._closing = False

        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        # Altura según el texto ya ajustado al ancho fijo (adjustSize no considera el salto de línea)
        layout.activate()
        self.setFixedHeight(max(56, layout.totalHeightForWidth(WIDTH)))

    # el tiempo se pausa mientras el mouse está encima
    def enterEvent(self, event):
        self.timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._closing: self.timer.start()
        super().leaveEvent(event)

    def popup(self, target: QPoint):
        self.move(target + QPoint(40, 0))
        self.show()
        self.raise_()
        self._animate(target, 0.0, 1.0, QEasingCurve.Type.OutCubic)
        self.timer.start()

    def slide_to(self, target: QPoint):
        if self._closing: return
        animation = QPropertyAnimation(self, b'pos', self)
        animation.setDuration(180)
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide = animation
        animation.start()

    def dismiss(self):
        if self._closing: return
        self._closing = True
        self.timer.stop()
        group = self._animate(self.pos() + QPoint(40, 0), 1.0, 0.0, QEasingCurve.Type.InCubic)
        group.finished.connect(self._remove)

    def _remove(self):
        self.manager.remove(self)
        self.deleteLater()

    def _animate(self, end, opacity_from, opacity_to, curve):
        group = QParallelAnimationGroup(self)
        move = QPropertyAnimation(self, b'pos', group)
        move.setDuration(220)
        move.setEndValue(end)
        move.setEasingCurve(curve)
        fade = QPropertyAnimation(self.effect, b'opacity', group)
        fade.setDuration(220)
        fade.setStartValue(opacity_from)
        fade.setEndValue(opacity_to)
        group.addAnimation(move)
        group.addAnimation(fade)
        self._group = group
        group.start()
        return group


class ToastManager(QWidget):
    """Apila los toasts de una ventana y los reacomoda al redimensionar."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.toasts: list[QToast] = []
        self.hide()
        window.installEventFilter(self)

    @classmethod
    def of(cls, widget) -> 'ToastManager':
        window = widget.window()
        manager = getattr(window, '_toast_manager', None)
        if manager is None:
            manager = window._toast_manager = cls(window)
        return manager

    def eventFilter(self, obj, event):
        if obj is self.window and event.type() == QEvent.Type.Resize:
            self.relayout(animate=False)
        return False

    def positions(self):
        top = TOP_OFFSET
        for toast in reversed(self.toasts):  # el más nuevo arriba
            yield toast, QPoint(self.window.width() - WIDTH - MARGIN, top)
            top += toast.height() + GAP

    def show_toast(self, *args, **kwargs):
        toast = QToast(self, *args, **kwargs)
        self.toasts.append(toast)
        while len(self.toasts) > 4:  # no tapar la ventana
            self.toasts[0].dismiss()
            self.toasts.pop(0)
        for item, point in self.positions():
            if item is toast:
                item.popup(point)
            else:
                item.slide_to(point)
        return toast

    def remove(self, toast):
        if toast in self.toasts:
            self.toasts.remove(toast)
        self.relayout()

    def relayout(self, animate=True):
        for toast, point in self.positions():
            if animate:
                toast.slide_to(point)
            else:
                toast.move(point)


def toast(widget, text, detail='', kind=KIND_SUCCESS, action=None, duration=4500):
    return ToastManager.of(widget).show_toast(text, detail, kind, action, duration)
