import logging
import os
from datetime import datetime

from PySide6.QtCore import QStandardPaths
from dotenv import load_dotenv

from functions import to_bool
from logger import logger

load_dotenv()

DEBUG = to_bool(os.getenv("DEBUG", False))

SHOW_BORDER = False

ORGANIZATION_NAME = 'synop'
APPLICATION_NAME = 'accountant'

APPDATA_DIR = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
DOCUMENTS_DIR = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)

DEFAULT_WORK_DIR = f'{DOCUMENTS_DIR}/concentrados'
DEFAULT_DATABASE_DIR = f'{APPDATA_DIR}/{ORGANIZATION_NAME}/{APPLICATION_NAME}/db.sqlite3'
DEFAULT_THEME = 'azul'

QSS_PATH = 'assets/base.qss'
ICON_PATH = 'assets/icon.svg'

if not os.path.exists(ICON_PATH):
    logger.warn('the base icon file does not exist')

if DEBUG:
    now = datetime.now()
    logger.debug(f'Debug mode is active {DEBUG}')
