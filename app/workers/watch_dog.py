import time
from pathlib import Path

from PySide6.QtCore import Signal, QObject
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class WatchdogHandler(FileSystemEventHandler):
    def __init__(self, worker):
        super().__init__()
        self.worker = worker

    def on_created(self, event):
        if not event.is_directory:
            self.worker.change.emit(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.worker.change.emit(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self.worker.change.emit(event.src_path)


class WatchdogWorkerBase(QObject):
    start = Signal()
    change = Signal(str)
    path = None

    def __init__(self):
        super().__init__()
        self.observer = Observer()
        self._running = True

    def on_start(self):
        handler = WatchdogHandler(self)

        if isinstance(self.path, Path): self.path.mkdir(parents=True, exist_ok=True)
        self.observer.schedule(handler, self.path, recursive=True)
        self.observer.start()

        try:
            while self._running:
                time.sleep(1)
        finally:
            self.observer.stop()
            self.observer.join()

    def stop(self):
        self._running = False


def WatchdogWorker(path):
    return type('WatchdogWorkerPath', (WatchdogWorkerBase,), {'path': path})
