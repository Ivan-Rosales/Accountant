from tortoise import Tortoise

from app.logs.logger import logger
from settings import DATABASE


class Database:
    config = DATABASE

    async def init(self):
        await Tortoise.init(**self.config)
        await Tortoise.generate_schemas()

        logger.info(f'Database initialized, config: {self.config}')
