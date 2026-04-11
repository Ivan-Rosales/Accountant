import os

from PySide6.QtCore import QStandardPaths

from logger import logger

DEBUG = True
SHOW_BORDER = False

ORGANIZATION_NAME = 'synop'
APPLICATION_NAME = 'accountant'

APPDATA_DIR = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
DOCUMENTS_DIR = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)

DEFAULT_WORK_DIR = f'{DOCUMENTS_DIR}/concentrados'
DEFAULT_DATABASE_DIR = f'{APPDATA_DIR}/{ORGANIZATION_NAME}/{APPLICATION_NAME}/db.sqlite3'

QSS_PATH = 'assets/base.qss'
ICON_PATH = 'assets/icon.png'

if not os.path.exists(ICON_PATH):
    logger.warn('the base icon file does not exist')
