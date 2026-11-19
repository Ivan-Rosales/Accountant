from PySide6.QtWidgets import QMessageBox

from app.widgets.message_dialog import QMessageDialog


class QConfirmMessageBox(QMessageDialog):
    """Confirmación Sí/No. Con `danger=True` el botón principal es rojo (acciones destructivas)."""

    def __init__(self, parent, message, yes_func=None, no_func=None, **kwargs):
        kwargs.setdefault('title', 'Confirmar')
        kwargs.setdefault('icon', QMessageBox.Icon.Question)
        yes_label = kwargs.get('yes_label', 'sí')
        no_label = kwargs.get('no_label', 'no')
        super().__init__(parent)

        self.setWindowTitle(kwargs['title'])
        self.setIcon(kwargs['icon'])
        self.setText(message)
        if kwargs.get('danger'): self.setDanger(True)
        if kwargs.get('detail'): self.setDetailedText(kwargs['detail'])

        no_btn = self.addButton(no_label, QMessageBox.ButtonRole.NoRole)
        yes_btn = self.addButton(yes_label, QMessageBox.ButtonRole.YesRole)
        self.setDefaultButton(yes_btn)

        self.exec()

        pressed_button = self.clickedButton()
        self.accepted_answer = pressed_button == yes_btn

        if pressed_button == yes_btn and callable(yes_func):
            yes_func()

        if pressed_button == no_btn and callable(no_func):
            no_func()


def confirm_delete(parent, items: list[str], what='registro', detail=''):
    """Pregunta antes de eliminar. Devuelve True si el usuario confirma."""
    count = len(items)
    noun = what if count == 1 else f'{what}s'
    listed = '\n'.join(f'• {i}' for i in items[:6]) + (f'\n• ... y {count - 6} más' if count > 6 else '')
    box = QConfirmMessageBox(
        parent,
        f'Se eliminará{"n" if count > 1 else ""} {count} {noun}:\n{listed}\n\nEsta acción no se puede deshacer.',
        title=f'¿Eliminar {noun}?', danger=True, yes_label='eliminar', no_label='cancelar', detail=detail,
    )
    return box.accepted_answer
