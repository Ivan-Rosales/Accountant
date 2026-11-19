from PySide6.QtCore import QObject, Signal

from app.core.excepthook import Log
from execution.year_summary import YearSummary
from models import Cliente


class YearSummaryWorker(QObject):
    start = Signal(object, int, int)
    success = Signal(object)
    progress = Signal(float)
    error = Signal(object)

    def on_start(self, client: Cliente, year, month):
        self.progress.emit(0)

        try:
            year_summary = YearSummary(client, year)
            sheet = year_summary.generate_sheet(month, replace=True)
            year_summary.order_sheets()

            year_summary.set_active_sheet(sheet.title)

            self.progress.emit(1)
            self.success.emit(year_summary)
        except Exception as error:
            log = Log('year_summary', {'client': client.to_dict() if isinstance(client, Cliente) else None, 'year': year, 'month': month})
            setattr(error, 'log', log)
            self.error.emit(error)
