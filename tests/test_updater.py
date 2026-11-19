import hashlib
import io
import sys

import pytest

import updater
from app.core import launch
from app.core.launch import UpdatingException, is_newer, parse_version, select_release_asset

PAYLOAD = b'MZ' + b'\x00' * 1000
SHA = hashlib.sha256(PAYLOAD).hexdigest()


def release(tag='1.7.0', digest=f'sha256:{SHA}', url='https://github.com/x/Contabilidad.exe'):
    return {'tag_name': tag, 'assets': [{'name': 'Contabilidad.exe', 'browser_download_url': url, 'digest': digest}]}


@pytest.mark.parametrize('remote, local, expected', [
    ('1.6.3', '1.6.2', True),
    ('v1.10.0', '1.9.9', True),
    ('1.6.2', '1.6.2', False),
    ('1.5.9', '1.6.2', False),  # nunca "actualizar" hacia atrás
    ('1.7', '1.7.0', False),
])
def test_is_newer(remote, local, expected):
    assert is_newer(remote, local) is expected


def test_parse_version_invalida():
    with pytest.raises(UpdatingException):
        parse_version('latest')


def test_select_release_asset():
    assert select_release_asset(release()) == ('1.7.0', 'https://github.com/x/Contabilidad.exe', SHA)


@pytest.mark.parametrize('data', [
    release(digest=None),
    release(digest='md5:abc'),
    release(url='http://github.com/x/Contabilidad.exe'),
    {'tag_name': '1.7.0', 'assets': []},
])
def test_select_release_asset_rechaza_inseguro(data):
    with pytest.raises(UpdatingException):
        select_release_asset(data)


def test_try_update_no_corre_desde_codigo_fuente(monkeypatch):
    monkeypatch.setattr(launch, 'AUTO_UPDATE', True)
    monkeypatch.delattr(sys, 'frozen', raising=False)
    monkeypatch.setattr(launch.requests, 'get', lambda *a, **k: pytest.fail('no debe consultar GitHub'))
    launch.try_update()


class FakeResponse(io.BytesIO):
    def __init__(self, data, length=None):
        super().__init__(data)
        self.length = len(data) if length is None else length

    def getheader(self, name, default=None):
        return str(self.length) if name == 'Content-Length' else default


def fake_urlopen(data, length=None):
    return lambda *a, **k: FakeResponse(data, length)


def test_download_verified_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(updater.urllib.request, 'urlopen', fake_urlopen(PAYLOAD))
    progress = []
    path = updater.download_verified('https://x/app.exe', tmp_path / 'app.exe', SHA, progress=progress.append)
    assert path.read_bytes() == PAYLOAD
    assert progress[-1] == 100


@pytest.mark.parametrize('data, length, sha', [
    (PAYLOAD, None, '0' * 64),  # firma distinta
    (PAYLOAD[:500], len(PAYLOAD), SHA),  # descarga cortada
])
def test_download_verified_falla_sin_dejar_archivo(tmp_path, monkeypatch, data, length, sha):
    monkeypatch.setattr(updater.urllib.request, 'urlopen', fake_urlopen(data, length))
    with pytest.raises(updater.DownloadError):
        updater.download_verified('https://x/app.exe', tmp_path / 'app.exe', sha)
    assert list(tmp_path.iterdir()) == []


def test_download_error_de_red(tmp_path, monkeypatch):
    def boom(*a, **k): raise OSError('sin red')
    monkeypatch.setattr(updater.urllib.request, 'urlopen', boom)
    with pytest.raises(updater.DownloadError):
        updater.download_verified('https://x/app.exe', tmp_path / 'app.exe', SHA)
    assert list(tmp_path.iterdir()) == []


def test_replace_executable(tmp_path):
    target = tmp_path / 'Contabilidad.exe'
    target.write_bytes(b'old')
    new = tmp_path / 'new.exe'
    new.write_bytes(b'new')
    updater.replace_executable(new, target, attempts=1, wait=0)
    assert target.read_bytes() == b'new'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['Contabilidad.exe']


def test_replace_executable_restaura_si_falla(tmp_path, monkeypatch):
    target = tmp_path / 'Contabilidad.exe'
    target.write_bytes(b'old')
    new = tmp_path / 'new.exe'
    new.write_bytes(b'new')

    def fail(*a, **k): raise OSError('en uso')
    monkeypatch.setattr(updater.shutil, 'move', fail)
    with pytest.raises(updater.DownloadError):
        updater.replace_executable(new, target, attempts=2, wait=0)
    assert target.read_bytes() == b'old'
