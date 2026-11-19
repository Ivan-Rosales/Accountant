import shutil
import tempfile
import zipfile
from pathlib import Path

from exceptions import ValidationException
from logger import logger

MAX_UNCOMPRESSED_BYTES = 1024 * 1024 * 1024  # 1 GB
MAX_FILES = 50_000


class ZipFile:
    """Extrae un ZIP de CFDI en una carpeta temporal propia que se borra al terminar.

    Uso:
        with ZipFile(path) as folder:
            ...
    """
    prefix = 'Accountant_'

    def __init__(self, path):
        self.path: Path = Path(path)
        self.extract_path: Path | None = None
        self.validate()

    def validate(self):
        if not self.path.is_file():
            raise ValidationException(f'No existe el archivo\n{self.path}')
        if not zipfile.is_zipfile(self.path):
            raise ValidationException(f'El archivo no es un ZIP válido\n{self.path}')

    def _check_limits(self, archive: zipfile.ZipFile):
        infos = archive.infolist()
        if len(infos) > MAX_FILES:
            raise ValidationException(f'El ZIP contiene demasiados archivos ({len(infos)})\n{self.path}')
        size = sum(i.file_size for i in infos)
        if size > MAX_UNCOMPRESSED_BYTES:
            raise ValidationException(f'El ZIP descomprimido excede 1 GB\n{self.path}')

    def extract(self) -> Path:
        # Carpeta única por extracción: dos ZIP procesados en el mismo segundo no se mezclan
        self.extract_path = Path(tempfile.mkdtemp(prefix=self.prefix))
        try:
            with zipfile.ZipFile(self.path, 'r') as archive:
                self._check_limits(archive)
                archive.extractall(self.extract_path)  # extractall ya descarta rutas absolutas y '..'
        except Exception:
            self.cleanup()
            raise

        logger.info(f'Extracted {self.path} file in {self.extract_path}')
        return self.extract_path

    def mark_processed(self):
        if not self.path.name.startswith('success'):
            self.path = self.path.rename(self.path.with_name(f'success - {self.path.name}'))

    def cleanup(self):
        if self.extract_path is not None:
            shutil.rmtree(self.extract_path, ignore_errors=True)
            self.extract_path = None

    def __enter__(self) -> Path:
        return self.extract()

    def __exit__(self, *_):
        self.cleanup()
