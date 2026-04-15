from PySide6.QtWidgets import QMessageBox, QStyle, QLabel, QGridLayout, QHBoxLayout, QPushButton, QTextEdit

from app.widgets.common import spacer
from base.dialog import BaseDialog


class QMessageDialog(BaseDialog):
    layout_class = QGridLayout
    icon_map = {
        QMessageBox.Icon.Warning: QStyle.StandardPixmap.SP_MessageBoxWarning,
        QMessageBox.Icon.Question: QStyle.StandardPixmap.SP_MessageBoxQuestion,
    }

    windows_size = (600, 100)
    _clickedButton = None
    details = 'mostrar detalles'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_buttons = []

    def create_ui(self):
        self.text = QLabel()
        self.icon_label = QLabel()
        self.detailed_text = QTextEdit()
        self.detailed_text.setReadOnly(True)

        self.icon_label.hide()
        self.detailed_text.hide()

    def load_ui(self, layout: QGridLayout):
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(0, 0)
        layout.setRowStretch(1, 0)
        layout.setRowStretch(2, 1)

        layout.addWidget(self.text, 0, 1)
        layout.addWidget(self.icon_label, 0, 0)
        layout.addWidget(self.detailed_text, 2, 0, 1, 2)

    def create_buttons(self):
        self.buttons = QHBoxLayout()
        self.buttons.addItem(spacer)

        diff = [i for i in self.default_buttons if i != self.details]
        if len(diff) == 0: self.insertButton('ok')

        for label in self.default_buttons:
            button = QPushButton(label.capitalize())
            button.clicked.connect(lambda name=label, *args, **kwargs: self.on_click(name))
            button.setMinimumWidth(50)

            self.buttons.addWidget(button)

            normalize_name = label.replace(' ', '_')
            setattr(self, f'btn_{normalize_name}', button)

        self._layout.addLayout(self.buttons, 1, 0, 1, 2)

    def setIcon(self, icon_enum):
        icon = self.icon_map.get(icon_enum)
        if icon is None: return

        style = self.style()
        pixmap = style.standardIcon(icon).pixmap(48, 48)
        self.icon_label.setPixmap(pixmap)
        self.icon_label.show()

    def setText(self, text):
        self.text.setText(text)
        self.text.show()

    def setDetailedText(self, text):
        if self.details not in self.default_buttons:
            self.addButton(self.details, None)
        self.detailed_text.setText(text)

    def addButton(self, text, _=None):
        self.default_buttons.append(text)
        return text

    def insertButton(self, text, index=0):
        self.default_buttons.insert(index, text)
        return text

    def setDefaultButton(self, *_, **__):
        pass

    def on_click(self, name):
        if name == self.details:
            is_visible = not self.detailed_text.isVisible()
            self.detailed_text.setVisible(is_visible)
            self.adjustSize()

            message = 'ocultar detalles'.capitalize() if is_visible else self.details.capitalize()
            self.detailed_text.setText(message)
            return

        self.hide()

        self._clickedButton = name

    def clickedButton(self):
        return self._clickedButton

    def adjustSize(self):
        super().adjustSize()
        self.setFixedWidth(self.windows_size[0])

    def exec(self):
        self.create_buttons()
        super().exec()
