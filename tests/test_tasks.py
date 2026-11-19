import threading
import time

import pytest
from PySide6.QtCore import QCoreApplication, QThreadPool

from app.core.tasks import TaskRunner


@pytest.fixture(scope='module')
def qapp():
    return QCoreApplication.instance() or QCoreApplication([])


def settle(qapp, runner):
    runner.wait(5000)
    for _ in range(10):
        qapp.processEvents()


class FakeOverlay:
    def __init__(self):
        self.calls = []

    def start(self, message=''): self.calls.append(('start', message))

    def stop(self): self.calls.append(('stop',))


def test_resultado_llega_en_el_hilo_de_la_interfaz(qapp):
    runner = TaskRunner(pool=QThreadPool())
    main = threading.get_ident()
    seen = {}

    def work():
        seen['worker'] = threading.get_ident()
        return 42

    runner.run('k', work, on_done=lambda r: seen.update(result=r, done=threading.get_ident()))
    settle(qapp, runner)
    assert seen['result'] == 42
    assert seen['worker'] != main and seen['done'] == main


def test_solo_entrega_la_ultima_llamada(qapp):
    runner = TaskRunner(pool=QThreadPool())
    results = []
    runner.run('mes', lambda: (time.sleep(0.2), 'enero')[1], on_done=results.append)
    runner.run('mes', lambda: 'febrero', on_done=results.append)
    settle(qapp, runner)
    assert results == ['febrero']


def test_error_y_overlay(qapp):
    runner = TaskRunner(pool=QThreadPool())
    overlay, errors = FakeOverlay(), []

    def boom(): raise ValueError('falló')

    runner.run('x', boom, on_error=errors.append, overlay=overlay, message='Cargando...')
    settle(qapp, runner)
    assert [str(e) for e in errors] == ['falló']
    assert overlay.calls == [('start', 'Cargando...'), ('stop',)]
    assert not runner.is_running('x')
