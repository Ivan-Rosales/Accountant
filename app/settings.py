import os
import sys
from datetime import datetime

from PySide6.QtCore import QStandardPaths
from dotenv import load_dotenv

from logger import logger

load_dotenv()

DEBUG = os.getenv("DEBUG", 'False') == 'True'
SHOW_PATHS = os.getenv("SHOW_PATHS", 'False') == 'True'
SHOW_BORDER = os.getenv("SHOW_BORDER", 'False') == 'True'

ORGANIZATION_NAME = 'synop'
APPLICATION_NAME = 'accountant'

BASE_PATH = getattr(sys, '_MEIPASS', os.path.abspath("."))
APPDATA_DIR = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
DOCUMENTS_DIR = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)

DEFAULT_WORK_DIR = f'{DOCUMENTS_DIR}/concentrados'
DEFAULT_DATABASE_DIR = f'{APPDATA_DIR}/{ORGANIZATION_NAME}/{APPLICATION_NAME}/db.sqlite3'
DEFAULT_THEME = 'azul'

ICON_PATH = f'{BASE_PATH}\\assets\\icon.svg'
QSS_PATH = f'{BASE_PATH}\\assets\\qss\\*.qss'

if not os.path.exists(ICON_PATH):
    logger.warn('the base icon file does not exist')

if DEBUG:
    now = datetime.now()
    logger.debug(f'Debug mode is active {DEBUG}')
