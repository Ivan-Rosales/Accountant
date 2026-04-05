import asyncio
import contextvars
import threading

from PySide6.QtCore import QObject, Signal, Slot
from tortoise import Tortoise
from tortoise.context import TortoiseContext

from core.logger import logger
from settings import DATABASE


class DatabaseWorker(QObject):
    result = Signal(object, object)
    error = Signal(object, object)
    ready = Signal()

    def __init__(self, **kwargs):
        super().__init__()
        self._config = kwargs.get('config', DATABASE)
        self._ctx_snapshot: contextvars.Context | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._started = False

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _init_db(self):
        self._tortoise_ctx = TortoiseContext()
        await self._tortoise_ctx.__aenter__()
        await Tortoise.init(**self._config)
        await Tortoise.generate_schemas()
        self._ctx_snapshot = contextvars.copy_context()
        logger.info(f'Database initialized, config:{self._config}')

    @Slot()
    def start(self):
        if self._started: return
        self._started = True

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        while self._loop is None or not self._loop.is_running():
            pass

        future = asyncio.run_coroutine_threadsafe(self._init_db(), self._loop)
        future.result()
        self.ready.emit()

    async def _wrapper(self, parent, coro_func, *args):
        try:
            results = await coro_func(*args)
            logger.debug(f'Database results coro_func:{coro_func} results:{results} parent:{parent}')
            self.result.emit(parent, results)
        except Exception as e:
            logger.debug(f'Database error coro_func:{coro_func} error:{e} parent:{parent}')
            self.error.emit(parent, e)

    def execute(self, parent, coro_func, *args):
        if not self._started: self.start()
        logger.debug(f'Database execution coro_func:{coro_func} parent:{parent}')
        if self._loop and self._loop.is_running() and self._ctx_snapshot:
            func = asyncio.run_coroutine_threadsafe
            self._ctx_snapshot.run(func, self._wrapper(parent, coro_func, *args), self._loop)

    @Slot()
    def stop(self):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._close(), self._loop)

    async def _close(self):
        if self._ctx: await self._ctx.__aexit__(None, None, None)
        await Tortoise.close_connections()
        self._loop.stop()
