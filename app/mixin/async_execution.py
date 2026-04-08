from PySide6.QtCore import QThread


class AsyncExecutionMixin:
    worker_class = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.worker_class:
            self.thread = QThread()
            self.worker = self.worker_class()
            self.worker.moveToThread(self.thread)
            self.worker.start.connect(self.worker.on_start)

            if hasattr(self, 'on_success'): self.worker.success.connect(self.on_success)
            if hasattr(self, 'on_error'): self.worker.error.connect(self.on_error)

            self.thread.start()

    def validate_data(self):
        return True

    def start_worker(self):
        data = self.validate_data()
        if data is None: return

        if isinstance(data, dict):
            self.worker.start.emit(**data)
        elif isinstance(data, (list, tuple)):
            self.worker.start.emit(*data)
        else:
            self.worker.start.emit(data)
