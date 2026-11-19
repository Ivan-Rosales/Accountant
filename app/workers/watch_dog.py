from pathlib import Path

from PySide6.QtCore import Signal, QObject
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from logger import logger


def is_relevant(path: str) -> bool:
    """Solo interesan los libros de Excel; se ignoran los archivos de bloqueo de Office (~$...)."""
    p = Path(path)
    return p.suffix.lower() == '.xlsx' and not p.name.startswith('~$')


class WatchdogHandler(FileSystemEventHandler):
    def __init__(self, worker):
        super().__init__()
        self.worker = worker

    def on_any_event(self, event):
        if event.is_directory or event.event_type not in ('created', 'modified', 'deleted', 'moved'):
            return
        for path in (event.src_path, getattr(event, 'dest_path', '')):
            if path and self.worker.relevant(str(path)):
                # Se emite desde el hilo del observer; Qt lo entrega en cola al hilo de la UI
                self.worker.change.emit(str(path))
                return


class WatchdogWorker(QObject):
    """Vigila una carpeta. El Observer de watchdog ya corre en su propio hilo, así que no bloquea ninguno de Qt."""
    start = Signal()
    change = Signal(str)

    def __init__(self, path=None, relevant=is_relevant, recursive=True):
        super().__init__()
        self.path: Path | None = Path(path) if path else None
        self.relevant = relevant
        self.recursive = recursive
        self.observer: Observer | None = None

    def on_start(self):
        self.stop()
        if self.path is None: return

        self.path.mkdir(parents=True, exist_ok=True)
        self.observer = Observer()
        self.observer.schedule(WatchdogHandler(self), str(self.path), recursive=self.recursive)
        self.observer.daemon = True
        self.observer.start()
        logger.info(f'Watching {self.path} on change')

    def set_path(self, path):
        self.path = Path(path) if path else None
        self.on_start()

    def stop(self):
        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None
