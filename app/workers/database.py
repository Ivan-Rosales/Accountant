from pathlib import Path

from PySide6.QtCore import QObject, Signal
from sqlalchemy import create_engine, select, inspect, update
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.settings import settings
from app.settings import DEFAULT_DATABASE_DIR
from logger import logger


def wrapper_model(register_model, func):
    def wrapper(emit_model, data):
        if register_model == emit_model:
            return func(data)
        return None

    return wrapper


class ModelMixin:
    @classmethod
    def on_change(cls, function):
        database_worker.on_change.connect(wrapper_model(cls, function))
        cls.all()

    @classmethod
    def all(cls):
        database_worker.execute.emit(lambda: database_worker.get_all(cls))

    @classmethod
    def create(cls, **kwargs):
        database_worker.execute.emit(lambda: database_worker.create(cls, **kwargs))

    @classmethod
    def get_or_create(cls, **kwargs):
        database_worker.execute.emit(lambda: database_worker.get_or_create(cls, **kwargs))

    @classmethod
    def update(cls, **kwargs):
        database_worker.execute.emit(lambda: database_worker.update(cls, **kwargs))

    @classmethod
    def delete(cls, instance):
        database_worker.execute.emit(lambda: database_worker.delete(cls, instance))

    def save(self, *args, **kwargs):
        database_worker.execute.emit(lambda: database_worker.save(self, *args, **kwargs))


class DatabaseWorker(QObject):
    execute = Signal(object)
    base = declarative_base()

    on_change = Signal(object, list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execute.connect(self.on_execute)
        self._session = None

    def reset(self, *_, **__):
        self._session = None

        models = self.base.registry.mappers
        for mapper in models:
            model = mapper.class_
            model.all()

    @property
    def session(self):
        if self._session is None:
            database_dir = settings.value('dbdir')
            if database_dir is None:
                logger.error('database path is not set')
                return None

            Path(database_dir).parent.mkdir(parents=True, exist_ok=True)
            engine = create_engine(f"sqlite:///{database_dir}", echo=False)
            logger.info(f'Database {database_dir}')
            self.base.metadata.create_all(engine)

            self._session = sessionmaker(bind=engine)()

        return self._session

    def on_execute(self, func):
        if callable(func): func()

    def get_all(self, model):
        rows = self.session.query(model).all()
        self.on_change.emit(model, rows)

    def get_or_create(self, model, **kwargs):
        instance = self.session.execute(select(model).filter_by(**kwargs)).scalar_one_or_none()
        create = instance is None
        if create: self.create(model, **kwargs)
        self.get_all(model)

    def create(self, model, **kwargs):
        instance = model(**kwargs)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        self.get_all(model)

    def update(self, model, **kwargs):
        pk = kwargs.pop('id')
        instance = self.session.get(model, pk)
        for key, value in kwargs.items():
            setattr(instance, key, value)
        self.session.commit()
        self.get_all(model)

    def delete(self, model, instance):
        self.session.delete(instance)
        self.session.commit()
        self.get_all(model)

    def save(self, instance):
        state = inspect(instance)
        fields = [attr.key for attr in state.attrs if attr.history.has_changes()]

        pk = getattr(instance, 'id')
        kwargs = {field: getattr(instance, field) for field in fields}

        self.session.execute(
            update(instance.__table__)
            .where(instance.__class__.id == pk)
            .values(**kwargs)
        )
        self.session.commit()
        self.get_all(instance.__class__)


database_worker = DatabaseWorker()
