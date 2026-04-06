import os

from PySide6.QtCore import QStandardPaths

from core.logger import logger

DEBUG = True

CONFIGURATION = ''

DOCUMENTS_DIR = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
DEFAULT_WORK_DIR = f'{DOCUMENTS_DIR}/concentrados'

QSS_PATH = 'assets/base.qss'
ICON_PATH = 'assets/icon_16x16.ico'

if not os.path.exists(ICON_PATH):
    logger.warn('the base icon file does not exist')

DATABASE = {
    'db_url': "sqlite://db.sqlite3",
    'modules': {
        'models': ['core.models'],
    }
}
