from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


def card(parent, title, subtitle=''):
    """Contenedor con título para agrupar opciones."""
    frame = QFrame(parent)
    frame.setProperty('class', 'card')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(8)
    heading = QLabel(title, frame)
    heading.setProperty('class', 'card-title')
    layout.addWidget(heading)
    if subtitle:
        hint = QLabel(subtitle, frame)
        hint.setProperty('class', 'secondary')
        hint.setWordWrap(True)
        layout.addWidget(hint)
    return frame, layout
