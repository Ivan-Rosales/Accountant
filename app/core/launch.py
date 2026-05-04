import os
import subprocess
import sys

import requests

from app.core.settings import config
from app.settings import BASE_PATH


def try_update():
    try:
        url = "https://api.github.com/repos/Ivan-Rosales/Accountant/releases/latest"
        response = requests.get(url).json()

        version = config['project']['version']
        last_version = response['tag_name']
        if version == last_version: return
        print(version, last_version)

        asset = next(i for i in response['assets'] if i.get('name') == 'Contabilidad.exe')
        url = asset['browser_download_url']

        pid = os.getpid()
        subprocess.Popen([f'{BASE_PATH}\\updater.exe', url, str(sys.executable), str(pid)])
    except:
        pass
