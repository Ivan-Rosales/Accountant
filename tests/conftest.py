"""Aislamiento de pruebas: nunca tocan la carpeta de concentrados, la BD ni la configuración reales."""
import locale
from pathlib import Path

import pytest

try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')  # igual que accountant.py
except locale.Error:
    pass

from app.core.settings import settings  # noqa: E402
from app.workers.database import database_worker  # noqa: E402
from models import Cliente  # noqa: E402
from tests.cases import CLIENTE_RFC  # noqa: E402

REAL_WORKDIR = Path(str(settings.value('workdir'))).resolve()


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    workdir = tmp_path / 'concentrados'
    overrides = {'workdir': str(workdir), 'dbdir': str(tmp_path / 'db.sqlite3')}
    original_value = settings.value

    def value(key, default=None):
        return overrides[key] if key in overrides else original_value(key, default)

    def forbid_write(*_, **__):
        pytest.fail('Las pruebas no deben escribir la configuración del usuario')

    monkeypatch.setattr(settings, 'value', value)
    monkeypatch.setattr(settings, 'setValue', forbid_write)
    monkeypatch.setattr(database_worker, '_session', None)
    monkeypatch.setattr(database_worker, '_engine', None)

    assert settings.get_workdir().resolve() != REAL_WORKDIR
    yield workdir

    if database_worker._session is not None:
        database_worker._session.close()
    if database_worker._engine is not None:
        database_worker._engine.dispose()


@pytest.fixture
def workdir(isolated_env):
    return isolated_env


@pytest.fixture
def cliente():
    return Cliente(id=1, rfc=CLIENTE_RFC, nombre='CLIENTE', apellido_paterno='DE', apellido_materno='PRUEBA')


@pytest.fixture
def xml_dir(tmp_path):
    path = tmp_path / 'xml'
    path.mkdir()
    return path
