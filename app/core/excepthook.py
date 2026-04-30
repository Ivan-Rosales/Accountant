import json
import shutil
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.settings import LOGS_DIR
from app.widgets.message_dialog import QMessageDialog
from base.popup import QDialogException
from logger import logger


@dataclass
class Log:
    name: str
    data: dict
    files: list = field(default_factory=list)


def except_hook(exc_type, exc_value, exc_traceback):
    if not isinstance(exc_value, QDialogException):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    cause = getattr(exc_value, '__cause__', exc_value)

    message_txt = exc_value.get_text()
    logger.error(f'{exc_type.__name__}: {message_txt.replace('\n', ' ')}')

    message = QMessageDialog(exc_value.parent)

    message.setIcon(exc_value.icon)
    message.setWindowTitle(exc_value.title.capitalize())

    message.setText(message_txt.capitalize() if exc_value.format else message_txt)

    detailed_text = ''.join(traceback.format_exception(type(cause), cause, getattr(cause, '__traceback__')))
    message.setDetailedText(detailed_text)

    if log := getattr(cause, 'log', None):
        log: Log
        now = datetime.now()
        log_name = f'log_{int(now.timestamp())}.json'
        log_file = Path(LOGS_DIR) / log_name
        log_file.parent.mkdir(parents=True, exist_ok=True)

        full_log = {
            'type': log.name,
            'data': {**log.data, 'message': message_txt, 'detail': detailed_text},
            'datetime': now.isoformat(),
        }

        json.dump(full_log, log_file.open('w'))

        for file in log.files:
            log_file = log_file.with_suffix('') / file.name
            log_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(file, log_file)

    message.exec()
