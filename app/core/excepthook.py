import sys
import traceback

from app.core.base_popup import QDialogException
from app.widgets.message_dialog import QMessageDialog


def except_hook(exc_type, exc_value, exc_traceback):
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

    if isinstance(exc_value, QDialogException):
        message = QMessageDialog(exc_value.parent)

        message.setIcon(exc_value.icon)
        message.setWindowTitle(exc_value.title.capitalize())

        message_txt = exc_value.get_text()
        message.setText(message_txt.capitalize() if exc_value.format else message_txt)

        detailed_text = traceback.format_exception(exc_type, exc_value, exc_traceback)
        message.setDetailedText(''.join(detailed_text))

        message.exec()
