import os

from core.logger import logger

DEBUG = True

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
