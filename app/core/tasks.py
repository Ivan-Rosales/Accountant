"""Tareas en segundo plano para que la interfaz no se congele.

    self.tasks = TaskRunner(self)
    self.tasks.run('cargar', funcion_lenta, on_done=self.mostrar, overlay=self.loader, message='Cargando...')

- `fn` corre en un hilo del QThreadPool: no debe tocar widgets.
- `on_done` / `on_error` corren en el hilo de la interfaz.
- Con la misma `key`, solo se entrega el resultado de la última llamada (si el usuario cambia de mes
  rápido, los resultados viejos se descartan).
"""
import itertools
import traceback

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from logger import logger


class _TaskSignals(QObject):
    finished = Signal(int, bool, object)


class _Task(QRunnable):
    def __init__(self, task_id, fn, signals):
        super().__init__()
        self.task_id, self.fn, self.signals = task_id, fn, signals
        self.setAutoDelete(True)

    def run(self):
        try:
            result = self.fn()
        except Exception as error:  # se entrega al hilo de la interfaz
            logger.error(f'Tarea en segundo plano falló: {error}\n{traceback.format_exc()}')
            self.signals.finished.emit(self.task_id, False, error)
        else:
            self.signals.finished.emit(self.task_id, True, result)


class TaskRunner(QObject):
    _ids = itertools.count(1)

    def __init__(self, parent=None, pool: QThreadPool | None = None):
        super().__init__(parent)
        self.pool = pool or QThreadPool.globalInstance()
        self.signals = _TaskSignals(self)  # vive en el hilo de la interfaz: la señal llega en cola
        self.signals.finished.connect(self._on_finished)
        self._latest: dict[str, int] = {}
        self._pending: dict[int, tuple] = {}

    def run(self, key, fn, on_done=None, on_error=None, overlay=None, message=''):
        task_id = next(self._ids)
        self._latest[key] = task_id
        self._pending[task_id] = (key, on_done, on_error, overlay)
        if overlay is not None: overlay.start(message)
        self.pool.start(_Task(task_id, fn, self.signals))
        return task_id

    def is_running(self, key) -> bool:
        return any(k == key for k, *_ in self._pending.values())

    @Slot(int, bool, object)
    def _on_finished(self, task_id, ok, payload):
        key, on_done, on_error, overlay = self._pending.pop(task_id, (None, None, None, None))
        if overlay is not None and not self.is_running(key):
            overlay.stop()
        if self._latest.get(key) != task_id:
            return  # resultado viejo: ya hay una llamada más reciente con la misma clave
        if ok:
            if on_done: on_done(payload)
        elif on_error:
            on_error(payload)
        else:
            logger.error(f'Error sin manejar en tarea {key}: {payload}')

    def wait(self, msecs=-1):
        return self.pool.waitForDone(msecs)
