from typing import Union

from app.core.db_worker import DatabaseWorker


class DatabaseMixin:
    db_worker = None

    error_function = None
    result_function = None

    def _on_error(self, *args, **kwargs):
        if callable(self.error_function):
            self.error_function(*args, **kwargs)
        else:
            print(args, kwargs)

        self.error_function = None

    def _on_success(self, *args, **kwargs):
        if callable(self.result_function):
            self.result_function(*args, **kwargs)
        self.result_function = None

    def execute_db(self, coro_func, signals=None):
        if signals is None: signals = {}

        self.error_function = signals.get('error', None)
        self.result_function = signals.get('success', None)

        db_worker = self.get_worker()
        db_worker.error.connect(self._on_error)
        db_worker.result.connect(self._on_success)
        self.db_worker.run_task(coro_func)

    def get_worker(self) -> Union[DatabaseWorker, None]:
        if self.db_worker is not None:
            return self.db_worker

        parent = self.parent()
        while parent is not None:
            if hasattr(parent, 'db_worker'):
                db_worker = getattr(parent, 'db_worker')
                setattr(self, 'db_worker', db_worker)
                return self.db_worker

            parent = parent.parent()

        return None
