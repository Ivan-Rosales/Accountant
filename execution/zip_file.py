import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from logger import logger


class ZipFile:
    prefix = 'Accountant'

    def __init__(self, path):
        self.path: Path = path

        folder = f'{self.prefix}_{int(datetime.now().timestamp())}'
        self.extract_path = Path(tempfile.gettempdir() + folder)
        self.validate()

    def validate(self):
        if not self.path.exists():
            raise Exception('Invalid path')

    def extract(self):
        zip_file = zipfile.ZipFile(self.path, 'r')
        zip_file.extractall(self.extract_path)
        zip_file.close()

        logger.info(f'Extracted {self.path} file in {self.extract_path}')
        if not self.path.name.startswith('success'):
            self.path.rename(self.path.with_name(f'success - {self.path.name}'))
        return self.extract_path
