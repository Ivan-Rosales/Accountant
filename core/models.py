from sqlalchemy import Column, Integer, String, Date, select, update
from sqlalchemy.orm import declarative_base

from core.database import engine, database_worker, SessionLocal
from core.logger import logger

Base = declarative_base()


class ModelMixin:
    @classmethod
    def connect_func(cls, func):
        database_worker.connect_func(cls, func)

    @classmethod
    def get_session(cls):
        if not hasattr(cls, 'session'):
            cls.session = SessionLocal()
        return cls.session

    @classmethod
    def all(cls):
        database_worker.all(cls)

    @classmethod
    def create(cls, **kwargs):
        database_worker.create(cls, **kwargs)

    @classmethod
    def get_or_create(cls, **kwargs):
        database_worker.get_or_create(cls, **kwargs)

    @classmethod
    def update(cls, **kwargs):
        database_worker.update(cls, **kwargs)

    @classmethod
    def delete(cls, instance):
        database_worker.delete(cls, instance)

    def save(self):
        database_worker.save(self.__class__, self)

    @classmethod
    def real_all(cls):
        session = cls.get_session()
        rows = session.query(cls).all()
        logger.info(f'{cls.__name__} read {rows}')
        return rows

    @classmethod
    def real_create(cls, **kwargs):
        session = cls.get_session()
        instance = cls(**kwargs)
        session.add(instance)
        session.commit()
        session.refresh(instance)
        logger.info(f'{cls.__name__} create {instance}')
        return instance

    @classmethod
    def real_get_or_create(cls, **kwargs):
        session = cls.get_session()
        instance = session.execute(select(cls).filter_by(**kwargs)).scalar_one_or_none()
        logger.info(f'{cls.__name__} get_or_create {instance}')
        if instance: return instance, False
        return cls.real_create(**kwargs), True

    @classmethod
    def real_update(cls, **kwargs):
        session = cls.get_session()
        pk = kwargs.pop('id')
        instance = session.get(cls, pk)
        for key, value in kwargs.items():
            setattr(instance, key, value)
        session.commit()
        logger.info(f'{cls.__name__} update.{pk} {instance}')
        return instance

    @classmethod
    def real_delete(cls, instance):
        session = cls.get_session()
        session.delete(instance)
        session.commit()
        logger.info(f'{cls.__name__} delete {instance}')

    def real_save(self):
        session = ModelMixin.get_session()

        kwargs = {i.name: getattr(self, i.name) for i in self.__table__.columns}
        pk = kwargs.pop('id')

        session.execute(
            update(self.__table__)
            .where(self.id == pk)
            .values(**kwargs)
        )
        session.commit()
        return self


class Cliente(Base, ModelMixin):
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100))
    apellido_paterno = Column(String(100), comment='apellido paterno')
    apellido_materno = Column(String(100), comment='apellido materno')
    rfc = Column(String(100), unique=True)
    __tablename__ = "client"

    def __str__(self):
        return f'({self.rfc}) {self.nombre} {self.apellido_paterno} {self.apellido_materno}'


class Metrica(Base, ModelMixin):
    id = Column(Integer, primary_key=True)
    fecha = Column(Date, unique=True)
    registers = Column(Integer, default=0)
    __tablename__ = "metrics"

    def __str__(self):
        return f'{self.fecha} {self.registers}'


Base.metadata.create_all(engine)
