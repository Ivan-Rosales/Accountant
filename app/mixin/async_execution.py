from PySide6.QtCore import QThread

from base.popup import QDialogException
from logger import logger


class AsyncExecutionMixin:
    worker_class = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.worker_class: return

        if not isinstance(self.worker_class, list):
            self.worker_class = [self.worker_class]

        for i, worker_class in enumerate(self.worker_class):
            self.register_worker(f'{i}', worker_class)

    def register_worker(self, key, worker_class):
        key = '' if key == '0' else f'_{key}'
        setattr(self, f'thread{key}', QThread())
        setattr(self, f'worker{key}', worker_class())
        getattr(self, f'worker{key}').moveToThread(getattr(self, f'thread{key}'))
        getattr(self, f'worker{key}').start.connect(getattr(self, f'worker{key}').on_start)

        worker = getattr(self, f'worker{key}')
        worker.success.connect(self.stop_loader)  # antes que on_success, que puede abrir un diálogo
        worker.error.connect(self.stop_loader)

        attr = f'on_success{key}'
        if hasattr(self, attr): getattr(self, f'worker{key}').success.connect(getattr(self, attr))

        attr = f'on_progress{key}'
        if hasattr(self, attr): getattr(self, f'worker{key}').progress.connect(getattr(self, attr))

        attr = f'on_error{key}'
        if hasattr(self, attr): getattr(self, f'worker{key}').error.connect(getattr(self, attr))

        getattr(self, f'thread{key}').start()

        logger.debug(f'Registered worker {key} {worker_class.__name__} in {self.__class__.__name__}')

    def validate_data(self):
        return True

    def start_worker(self):
        try:
            data = self.validate_data()
        except Exception as error:
            raise QDialogException(self, str(error), format=False) from error

        if data is None: return

        logger.info(f'{self.__class__.__name__} start, data: {data}')

        if isinstance(data, dict):
            self.worker.start.emit(**data)
        elif isinstance(data, (list, tuple)):
            self.worker.start.emit(*data)
        else:
            self.worker.start.emit(data)

        self.execute_btn.setEnabled(False)
        if loader := getattr(self, 'loader', None):
            loader.start(getattr(self, 'busy_message', 'Procesando...'))

    def stop_loader(self, *_):
        if loader := getattr(self, 'loader', None):
            loader.stop()

    def on_success(self, *args, **kwargs):
        raise NotImplementedError

    def on_progress(self, progress):
        logger.debug(f'{self.__class__.__name__}, progress: {progress}')

        self.execute_btn.setProgress(progress)

    def on_error(self, error):
        logger.error(f'{self.__class__.__name__}, error: {error}')

        self.execute_btn.setEnabled(True)
        self.execute_btn.resetProgress()

        raise QDialogException(self, str(error), format=False) from error
