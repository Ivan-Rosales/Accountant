import os
import time
import zipfile
from datetime import date

import pytest

from app.core.excepthook import prune_logs
from app.workers.database import database_worker
from app.workers.watch_dog import is_relevant
from exceptions import ValidationException
from execution import zip_file as zip_module
from execution.zip_file import ZipFile
from models import Metrica


def make_zip(path, files):
    with zipfile.ZipFile(path, 'w') as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


def test_zip_carpetas_unicas_y_limpieza(tmp_path):
    a = ZipFile(make_zip(tmp_path / 'a.zip', {'1.xml': '<a/>'}))
    b = ZipFile(make_zip(tmp_path / 'b.zip', {'2.xml': '<b/>'}))
    with a as folder_a, b as folder_b:
        assert folder_a != folder_b  # mismo segundo, carpetas distintas
        assert [p.name for p in folder_a.iterdir()] == ['1.xml']
    assert not folder_a.exists() and not folder_b.exists()


def test_zip_no_se_renombra_si_falla(tmp_path):
    path = make_zip(tmp_path / 'enero.zip', {'1.xml': '<a/>'})
    zip_file = ZipFile(path)
    with pytest.raises(RuntimeError):
        with zip_file:
            raise RuntimeError('fallo al procesar')
    assert path.exists()
    zip_file.mark_processed()
    assert (tmp_path / 'success - enero.zip').exists()


def test_zip_invalido(tmp_path):
    bad = tmp_path / 'no.zip'
    bad.write_text('hola')
    with pytest.raises(ValidationException):
        ZipFile(bad)


def test_zip_limite_tamano(tmp_path, monkeypatch):
    monkeypatch.setattr(zip_module, 'MAX_UNCOMPRESSED_BYTES', 10)
    zip_file = ZipFile(make_zip(tmp_path / 'big.zip', {'1.xml': 'x' * 100}))
    with pytest.raises(ValidationException):
        zip_file.extract()
    assert zip_file.extract_path is None


@pytest.mark.parametrize('path, expected', [
    (r'C:\c\RFC\RFC 2025 INGRESOS.xlsx', True),
    (r'C:\c\RFC\~$RFC 2025 INGRESOS.xlsx', False),
    (r'C:\c\RFC\proveedores\x.txt', False),
])
def test_watchdog_filtra(path, expected):
    assert is_relevant(path) is expected


def test_metrica_increment_y_rollback():
    hoy = date(2025, 1, 15)
    database_worker.on_execute(lambda: database_worker.increment(Metrica, 'registers', 3, fecha=hoy))
    database_worker.on_execute(lambda: database_worker.increment(Metrica, 'registers', 2, fecha=hoy))

    # Un commit fallido (fecha duplicada) no debe dejar la sesión inutilizable
    def duplicate():
        database_worker.session.add(Metrica(fecha=hoy, registers=1))
        database_worker.session.commit()
    database_worker.on_execute(duplicate)

    rows = database_worker.session.query(Metrica).all()
    assert [(m.fecha, m.registers) for m in rows] == [(hoy, 5)]


def test_prune_logs(tmp_path):
    for i in range(5):
        log = tmp_path / f'log_{i}.json'
        log.write_text('{}')
        os.utime(log, (time.time() + i, time.time() + i))
    prune_logs(tmp_path, keep=2)
    assert sorted(p.name for p in tmp_path.iterdir()) == ['log_3.json', 'log_4.json']
