from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, Signal

from app.core.excepthook import Log
from execution.month_summary import MonthSummary
from execution.month_summary_providers import MonthSummaryProviders
from execution.zip_file import ZipFile
from models import Cliente


class MonthSummaryWorker(QObject):
    start = Signal(list, object, object)
    success = Signal(object, int)
    progress = Signal(float)
    error = Signal(object)

    default_params = {
        'create_providers': False,
    }

    @staticmethod
    def get_steps(base_steps, params):
        if params['create_providers']:
            base_steps *= 2

        return base_steps

    def on_start(self, paths: List[Path], client: Cliente, params=None):
        params = self.default_params | (params or {})
        create_providers = params['create_providers']

        self.progress.emit(0)

        try:
            summary = None
            n_files = self.get_steps(len(paths), params)
            for c, path in enumerate(paths, 1):
                zipfile = ZipFile(path)
                data_path = zipfile.extract()

                summary = MonthSummary(client)
                summary.add_files_in_folder(data_path)
                summary.save()

                if create_providers:
                    self.progress.emit((c * 2 - 1) / n_files)

                    summary_providers = MonthSummaryProviders(client)
                    summary_providers.add_files_in_folder(data_path)
                    summary_providers.save()

                    self.progress.emit(c * 2 / n_files)
                else:
                    self.progress.emit(c / n_files)

            self.success.emit(summary, n_files)
        except Exception as error:
            log = Log(
                'month_summary',
                {'paths': [str(p.absolute()) for p in paths], 'client': client.to_dict(), 'params': params},
                paths,
            )
            setattr(error, 'log', log)
            self.error.emit(error)
