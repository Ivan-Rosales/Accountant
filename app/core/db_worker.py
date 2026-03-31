import asyncio

from PySide6.QtCore import QObject, Slot, Signal

from db.database import Database


class DatabaseWorker(QObject):
    result = Signal(object)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()

    async def execution(self, coro_func):
        database = Database()
        await database.init()

        return await coro_func()

    @Slot(object)
    def run_task(self, coro_func):
        try:
            result = self.loop.run_until_complete(self.execution(coro_func))
            self.result.emit(result)
        except Exception as e:
            self.error.emit(str(e))
