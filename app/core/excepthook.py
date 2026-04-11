import sys
import traceback

from app.widgets.message_dialog import QMessageDialog
from base.popup import QDialogException
from logger import logger


def except_hook(exc_type, exc_value, exc_traceback):
    if not isinstance(exc_value, QDialogException):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    message_txt = exc_value.get_text()
    logger.error(f'{exc_type.__name__}: {exc_value.get_text().replace('\n', ' ')}')

    message = QMessageDialog(exc_value.parent)

    message.setIcon(exc_value.icon)
    message.setWindowTitle(exc_value.title.capitalize())

    message.setText(message_txt.capitalize() if exc_value.format else message_txt)

    detailed_text = traceback.format_exception(exc_type, exc_value, exc_traceback)
    message.setDetailedText(''.join(detailed_text))

    message.exec()
