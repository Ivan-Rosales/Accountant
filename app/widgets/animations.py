"""Animaciones reutilizables (Qt no tiene transiciones en QSS: se hacen con QPropertyAnimation)."""
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QPoint
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect

FAST, NORMAL = 140, 220


def fade_in(widget: QWidget, duration=NORMAL, slide=0):
    """Aparece desde transparente (y opcionalmente sube `slide` px). Quita el efecto al terminar:
    QGraphicsOpacityEffect cuesta rendimiento si se deja puesto en widgets grandes."""
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)

    group = QParallelAnimationGroup(widget)
    opacity = QPropertyAnimation(effect, b'opacity', group)
    opacity.setDuration(duration)
    opacity.setStartValue(0.0)
    opacity.setEndValue(1.0)
    opacity.setEasingCurve(QEasingCurve.Type.OutCubic)
    group.addAnimation(opacity)

    if slide:
        end = widget.pos()
        move = QPropertyAnimation(widget, b'pos', group)
        move.setDuration(duration)
        move.setStartValue(end + QPoint(0, slide))
        move.setEndValue(end)
        move.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(move)

    group.finished.connect(lambda: widget.setGraphicsEffect(None))
    widget._fade_animation = group  # mantener referencia mientras corre
    group.start()
    return group


def window_fade_in(window: QWidget, duration=FAST):
    """Entrada de una ventana (modal) animando windowOpacity, más barato que un efecto gráfico."""
    animation = QPropertyAnimation(window, b'windowOpacity', window)
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    window._window_animation = animation
    animation.start()
    return animation
