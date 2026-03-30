from typing import Union

from app.core.db_worker import DatabaseWorker


class DatabaseMixin:
    db_worker = None

    def execute_db(self, coro_func, signals=None):
        if signals is None: signals = {}

        db_worker = self.get_worker()

        success_function = signals.get('success', None)
        if success_function: db_worker.result.connect(success_function)

        error_function = signals.get('error', None)
        if error_function: db_worker.error.connect(error_function)

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
