import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

from app.core.settings import config
from app.settings import BASE_PATH, REPO_URL, AUTO_UPDATE


class UpdatingException(Exception):
    pass


def try_update():
    if not AUTO_UPDATE: return

    try:
        url = REPO_URL
        response = requests.get(url).json()

        version = config['project']['version']
        last_version = response['tag_name']
        if version == last_version: return

        asset = next(i for i in response['assets'] if i.get('name') == 'Contabilidad.exe')
        url = asset['browser_download_url']

        path = Path(f'{BASE_PATH}\\updater.exe')
        temp_dir = Path(tempfile.gettempdir())
        dst_path = temp_dir / 'updater.exe'
        shutil.copy2(path, dst_path)

        subprocess.Popen([dst_path.absolute(), url, str(sys.executable), last_version])
        sys.exit(0)
    except Exception as e:
        log_file = open('updater.log', 'w')
        log_file.write(str(e))
        log_file.close()
