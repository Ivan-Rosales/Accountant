from pathlib import Path

from PySide6.QtCore import QObject, Signal
from sqlalchemy import create_engine, select, inspect, update
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.settings import settings
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

    @classmethod
    def increment(cls, field, amount, **filters):
        """Suma `amount` a `field` en el hilo de la BD (sin mutar objetos ORM desde la UI)."""
        database_worker.execute.emit(lambda: database_worker.increment(cls, field, amount, **filters))


class DatabaseWorker(QObject):
    execute = Signal(object)
    base = declarative_base()

    on_change = Signal(object, list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execute.connect(self.on_execute)
        self._session = None
        self._engine = None
        self._engine_path = None

    def reset(self, *_, **__):
        if self._session is not None: self._session.close()
        self._session = None
        self._engine = None

        models = self.base.registry.mappers
        for mapper in models:
            model = mapper.class_
            model.all()

    @property
    def engine(self):
        database_dir = settings.value('dbdir')
        if database_dir is None:
            logger.error('Database path is not defined')
            return None

        if self._engine is None or self._engine_path != database_dir:
            Path(database_dir).parent.mkdir(parents=True, exist_ok=True)
            # check_same_thread=False: los workers usan sesiones propias sobre el mismo archivo
            self._engine = create_engine(f"sqlite:///{database_dir}", echo=False,
                                         connect_args={'check_same_thread': False, 'timeout': 30})
            self._engine_path = database_dir
            logger.info(f'Database {database_dir}')
            self.base.metadata.create_all(self._engine)

        return self._engine

    @property
    def session(self):
        """Sesión del hilo de la base de datos (la usan los modelos de la interfaz)."""
        if self._session is None:
            engine = self.engine
            if engine is None: return None
            self._session = sessionmaker(bind=engine)()

        return self._session

    def new_session(self):
        """Sesión independiente para usar dentro de un worker (un hilo distinto al de la BD)."""
        return sessionmaker(bind=self.engine, expire_on_commit=False)()

    def on_execute(self, func):
        if not callable(func): return
        try:
            func()
        except Exception as error:
            # Sin rollback la sesión queda inutilizable después de un commit fallido
            logger.error(f'Database operation failed: {error}')
            if self._session is not None:
                self._session.rollback()

    def increment(self, model, field, amount, **filters):
        logger.debug(f'Incrementing {model.__name__}.{field} by {amount} {filters}')

        instance = self.session.execute(select(model).filter_by(**filters)).scalar_one_or_none()
        if instance is None:
            instance = model(**filters)
            setattr(instance, field, 0)
            self.session.add(instance)
        setattr(instance, field, (getattr(instance, field) or 0) + amount)
        self.session.commit()
        self.get_all(model)

    def get_all(self, model):
        logger.debug(f'Getting {model.__name__}')

        rows = self.session.query(model).all()
        self.on_change.emit(model, rows)

    def get_or_create(self, model, **kwargs):
        logger.debug(f'Getting or creating {model.__name__} {kwargs}')

        instance = self.session.execute(select(model).filter_by(**kwargs)).scalar_one_or_none()
        create = instance is None
        if create: self.create(model, **kwargs)
        self.get_all(model)

    def create(self, model, **kwargs):
        logger.debug(f'Creating {model.__name__} {kwargs}')

        instance = model(**kwargs)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        self.get_all(model)

    def update(self, model, **kwargs):
        logger.debug(f'Updating {model.__name__} {kwargs}')

        pk = kwargs.pop('id')
        instance = self.session.get(model, pk)
        for key, value in kwargs.items():
            setattr(instance, key, value)
        self.session.commit()
        self.get_all(model)

    def delete(self, model, instance):
        logger.debug(f'Deleting {model.__name__} {instance}')

        self.session.delete(instance)
        self.session.commit()
        self.get_all(model)

    def save(self, instance):
        logger.debug(f'Saving {instance.__class__.__name__} {instance}')

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
