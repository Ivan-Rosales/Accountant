from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, Signal

from app.core.excepthook import Log
from execution.month_summary import MonthSummary
from execution.month_summary_providers import MonthSummaryProviders
from execution.zip_file import ZipFile
from exceptions import ValidationException
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
            if not isinstance(client, Cliente):
                raise ValidationException('Seleccione un cliente antes de generar el concentrado')
            if not paths:
                raise ValidationException('Seleccione al menos un archivo ZIP')

            summary = None
            n_files = self.get_steps(len(paths), params)
            for c, path in enumerate(paths, 1):
                zipfile = ZipFile(path)
                with zipfile as data_path:
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

                zipfile.mark_processed()

            self.success.emit(summary, n_files)
        except Exception as error:
            log = Log(
                'month_summary',
                {
                    'paths': [str(Path(p).absolute()) for p in paths],
                    'client': client.to_dict() if isinstance(client, Cliente) else None,
                    'params': params,
                },
            )
            setattr(error, 'log', log)
            self.error.emit(error)
