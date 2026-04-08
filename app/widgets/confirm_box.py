from PySide6.QtWidgets import QMessageBox

from app.widgets.message_dialog import QMessageDialog


class QConfirmMessageBox(QMessageDialog):
    def __init__(self, parent, message, yes_func=None, no_func=None, **kwargs):
        kwargs.setdefault('title', 'Question')
        kwargs.setdefault('icon', QMessageBox.Icon.Question)
        super().__init__(parent)

        self.setWindowTitle(kwargs['title'])
        self.setIcon(kwargs['icon'])
        self.setText(message)

        yes_btn = self.addButton('Si', QMessageBox.ButtonRole.YesRole)
        no_btn = self.addButton('No', QMessageBox.ButtonRole.YesRole)
        self.setDefaultButton(yes_btn)

        self.exec()

        pressed_button = self.clickedButton()

        if pressed_button == yes_btn and callable(yes_func):
            yes_func()

        if pressed_button == no_btn and callable(no_func):
            no_func()
