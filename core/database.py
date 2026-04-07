from pathlib import Path

from PySide6.QtCore import QObject, Signal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.logger import logger
from settings import DATABASE_DIR

Path(DATABASE_DIR).parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DATABASE_DIR}", echo=False)
SessionLocal = sessionmaker(bind=engine)
logger.info(f'Database {DATABASE_DIR}')


def model_required(func):
    def wrapper(self, model, *args, **kwargs):
        if model not in self.registered_models:
            self._register_model(model, func.__name__ != 'connect_func')
        return func(self, model, *args, **kwargs)

    return wrapper


class DatabaseWorker(QObject):
    registered_models = dict()
    change = Signal(object, object)

    def _register_model(self, model, load=True):
        self.registered_models[model] = None
        if load: self.all(model)

        logger.info(f'{model.__name__} registered')

    def model_response(self, model, func):
        def wrapper(response_model, data):
            if model != response_model: return None
            return func(data)

        return wrapper

    @model_required
    def connect_func(self, model, func):
        self.change.connect(self.model_response(model, func))
        self.all(model)

    @model_required
    def all(self, model):
        rows = self.registered_models.get(model)
        if rows is None:
            rows = {row.id: row for row in model.real_all()}
            self.registered_models[model] = rows

        values = list(rows.values())
        logger.info(f'{model.__name__} emit {len(values)} rows')
        self.change.emit(model, values)

    @model_required
    def create(self, model, **kwargs):
        instance = model.real_create(**kwargs)
        self.registered_models[model][instance.id] = instance
        self.all(model)

    @model_required
    def get_or_create(self, model, **kwargs):
        instance, is_new = model.real_get_or_create(**kwargs)
        if is_new:
            self.registered_models[model][instance.id] = instance
            self.all(model)

    @model_required
    def update(self, model, **kwargs):
        instance = model.real_update(**kwargs)
        self.registered_models[model][instance.id] = instance
        self.all(model)

    @model_required
    def delete(self, model, instance):
        model.real_delete(instance)
        del self.registered_models[model][instance.id]
        self.all(model)

    @model_required
    def save(self, model, instance):
        instance = model.real_save(instance)
        self.registered_models[model][instance.id] = instance
        self.all(model)


database_worker = DatabaseWorker()
