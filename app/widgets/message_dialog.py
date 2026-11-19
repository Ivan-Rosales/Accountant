"""Modal estándar de la aplicación: ícono, título, mensaje, detalles opcionales y botones a la derecha.

Conserva la interfaz de QMessageBox que ya usa el código (setIcon, setText, setDetailedText,
addButton, setDefaultButton, exec, clickedButton).
"""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtWidgets import QMessageBox, QLabel, QGridLayout, QHBoxLayout, QPushButton, QTextEdit, QWidget, \
    QVBoxLayout

from base.dialog import BaseDialog

KIND_INFO, KIND_WARNING, KIND_QUESTION, KIND_DANGER, KIND_SUCCESS = 'info', 'warning', 'question', 'danger', 'success'
ICON_KINDS = {
    QMessageBox.Icon.Information: KIND_INFO,
    QMessageBox.Icon.Warning: KIND_WARNING,
    QMessageBox.Icon.Question: KIND_QUESTION,
    QMessageBox.Icon.Critical: KIND_DANGER,
}
KIND_STYLE = {  # color, símbolo
    KIND_INFO: (None, 'i'),
    KIND_QUESTION: (None, '?'),
    KIND_WARNING: ('#d29922', '!'),
    KIND_DANGER: ('#f85149', '!'),
    KIND_SUCCESS: ('#3fb950', '✓'),
}


class QModalIcon(QWidget):
    """Círculo de color con un símbolo; info y pregunta usan el color del tema."""

    def __init__(self, parent=None, kind=KIND_INFO, size=40):
        super().__init__(parent)
        self.kind = kind
        self.size_px = size
        self.setFixedSize(size, size)

    def set_kind(self, kind):
        self.kind = kind
        self.update()

    def paintEvent(self, _):
        from app.widgets.switch import QSwitch
        color, symbol = KIND_STYLE.get(self.kind, KIND_STYLE[KIND_INFO])
        color = QColor(color or QSwitch.accent)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        background = QColor(color)
        background.setAlpha(45)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        box = QRectF(0, 0, self.size_px, self.size_px)
        painter.drawEllipse(box)

        font = QFont(self.font())
        font.setPointSize(max(9, int(self.size_px * 0.35)))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, symbol)
        painter.end()


class QMessageDialog(BaseDialog):
    layout_class = QGridLayout
    margin = (24, 48, 24, 20)
    spacing = 14
    windows_size = (480, 160)

    details = 'mostrar detalles'
    _clickedButton = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El título va en el cuerpo del modal; la barra solo conserva el botón de cerrar
        for name in ('titleLabel', 'iconLabel'):
            if label := getattr(self.titleBar, name, None):
                label.hide()
        self.default_buttons = []
        self.primary_button = None
        self.danger = False

    def create_ui(self):
        self.icon = QModalIcon(self)
        self.heading = QLabel(self)
        self.heading.setProperty('class', 'modal-title')
        self.heading.setWordWrap(True)
        self.text = QLabel(self)
        self.text.setProperty('class', 'modal-text')
        self.text.setWordWrap(True)
        self.text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.detailed_text = QTextEdit(self)
        self.detailed_text.setReadOnly(True)
        self.detailed_text.setMinimumHeight(140)
        self.detailed_text.hide()

    def load_ui(self, layout: QGridLayout):
        layout.setColumnStretch(1, 1)
        text_box = QVBoxLayout()
        text_box.setSpacing(6)
        text_box.addWidget(self.heading)
        text_box.addWidget(self.text)
        layout.addWidget(self.icon, 0, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text_box, 0, 1)
        layout.addWidget(self.detailed_text, 2, 0, 1, 2)

    # ---- API tipo QMessageBox -------------------------------------------------
    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        self.heading.setText(str(title))

    def setIcon(self, icon_enum):
        self.icon.set_kind(ICON_KINDS.get(icon_enum, icon_enum if isinstance(icon_enum, str) else KIND_INFO))

    def setText(self, text):
        self.text.setText(text)

    def setDetailedText(self, text):
        if self.details not in self.default_buttons:
            self.default_buttons.insert(0, self.details)
        self.detailed_text.setText(text)

    def addButton(self, text, _=None):
        self.default_buttons.append(text)
        return text

    def insertButton(self, text, index=0):
        self.default_buttons.insert(index, text)
        return text

    def setDefaultButton(self, button, *_):
        self.primary_button = button

    def setDanger(self, danger=True):
        self.danger = danger
        self.icon.set_kind(KIND_DANGER if danger else self.icon.kind)

    # ---- construcción -----------------------------------------------------------
    def create_buttons(self):
        actions = [b for b in self.default_buttons if b != self.details]
        if not actions:
            self.default_buttons.append('aceptar')
            actions = ['aceptar']
        primary = self.primary_button if self.primary_button in actions else actions[-1]

        row = QHBoxLayout()
        row.setSpacing(8)
        if self.details in self.default_buttons:
            row.addWidget(self._button(self.details, flat=True))
        row.addStretch(1)
        # el botón principal siempre a la derecha
        for label in [a for a in actions if a != primary] + [primary]:
            button = self._button(label, primary=label == primary)
            row.addWidget(button)
            if label == primary:
                button.setDefault(True)
                button.setFocus()
        self._layout.addLayout(row, 3, 0, 1, 2)

    def _button(self, label, primary=False, flat=False):
        button = QPushButton(label[:1].upper() + label[1:], self)
        button.setMinimumWidth(96)
        if primary:
            button.setProperty('class', 'danger' if self.danger else 'primary')
        if flat:
            button.setProperty('type', 'flat')
        button.clicked.connect(lambda *_, w=button, name=label: self.on_click(w, name))
        setattr(self, f'btn_{label.replace(" ", "_")}', button)
        return button

    def on_click(self, widget, name):
        if name == self.details:
            visible = not self.detailed_text.isVisible()
            self.detailed_text.setVisible(visible)
            widget.setText('Ocultar detalles' if visible else 'Mostrar detalles')
            self.adjustSize()
            return
        self._clickedButton = name
        self.hide()

    def clickedButton(self):
        return self._clickedButton

    def adjustSize(self):
        super().adjustSize()
        self.setFixedWidth(self.windows_size[0])

    def exec(self):
        self.create_buttons()
        self.adjustSize()
        return super().exec()
