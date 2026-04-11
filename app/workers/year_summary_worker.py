from PySide6.QtCore import QObject, Signal

from execution.year_summary import YearSummary


class YearSummaryWorker(QObject):
    start = Signal(object, int, int)
    success = Signal(object)
    progress = Signal(float)
    error = Signal(object)

    def on_start(self, client, year, month):
        self.progress.emit(0)

        try:
            year_summary = YearSummary(client, year)
            year_summary.generate_sheet(month)
            year_summary.save()

            self.progress.emit(1)
            self.success.emit(year_summary)
        except Exception as error:
            self.error.emit(error)
