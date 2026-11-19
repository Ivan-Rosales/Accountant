import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import requests

from app.core.settings import config
from app.settings import BASE_PATH, REPO_URL, AUTO_UPDATE, LOGS_DIR
from logger import logger

ASSET_NAME = 'Contabilidad.exe'
REQUEST_TIMEOUT = 5


class UpdatingException(Exception):
    pass


def parse_version(version: str) -> tuple:
    """'v1.6.2' -> (1, 6, 2). Lanza UpdatingException si no es una versión válida."""
    match = re.fullmatch(r'v?(\d+(?:\.\d+)*)', str(version).strip())
    if not match:
        raise UpdatingException(f'Versión inválida: {version!r}')
    return tuple(int(i) for i in match.group(1).split('.'))


def is_newer(remote: str, local: str) -> bool:
    a, b = parse_version(remote), parse_version(local)
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def select_release_asset(release: dict) -> tuple[str, str, str]:
    """Devuelve (versión, url, sha256) del ejecutable publicado en el release.

    Exige el digest SHA-256 que GitHub publica para cada asset; sin él no se actualiza.
    """
    version = release['tag_name']
    asset = next((i for i in release.get('assets', []) if i.get('name') == ASSET_NAME), None)
    if asset is None:
        raise UpdatingException(f'El release {version} no contiene {ASSET_NAME}')

    url = asset.get('browser_download_url', '')
    if not url.startswith('https://'):
        raise UpdatingException(f'URL de descarga no segura: {url!r}')

    digest = asset.get('digest') or ''
    algorithm, _, value = digest.partition(':')
    if algorithm != 'sha256' or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise UpdatingException(f'El release {version} no publica un SHA-256 válido para {ASSET_NAME}')

    return version, url, value


def _write_log(error: Exception):
    try:
        path = Path(LOGS_DIR) / 'updater.log'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as log_file:
            log_file.write(f'{datetime.now().isoformat()} {type(error).__name__}: {error}\n')
    except OSError:
        pass


def try_update():
    if not AUTO_UPDATE: return

    # Solo el ejecutable empaquetado se actualiza: desde el código fuente sys.executable es python.exe
    if not getattr(sys, 'frozen', False):
        logger.debug('Actualización omitida: no es un ejecutable empaquetado')
        return

    try:
        response = requests.get(REPO_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        release = response.json()

        local_version = config['project']['version']
        if not is_newer(release['tag_name'], local_version): return

        version, url, sha256 = select_release_asset(release)

        updater = Path(BASE_PATH) / 'updater.exe'
        dst_path = Path(tempfile.gettempdir()) / 'accountant-updater.exe'
        shutil.copy2(updater, dst_path)

        subprocess.Popen([str(dst_path), url, str(sys.executable), version, sha256])
        sys.exit(0)
    except Exception as error:
        logger.warning(f'No se pudo buscar actualización: {error}')
        _write_log(error)
