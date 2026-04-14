from sqlalchemy import Column, Integer, String, Date

from app.workers.database import ModelMixin, DatabaseWorker


class Cliente(DatabaseWorker.base, ModelMixin):
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100))
    apellido_paterno = Column(String(100), comment='apellido paterno')
    apellido_materno = Column(String(100), comment='apellido materno')
    rfc = Column(String(100), unique=True)
    __tablename__ = "client"

    def fullname(self):
        return f'{self.nombre} {self.apellido_paterno} {self.apellido_materno}'

    def __str__(self):
        return f'({self.rfc}) {self.fullname()}'


class Metrica(DatabaseWorker.base, ModelMixin):
    id = Column(Integer, primary_key=True)
    fecha = Column(Date, unique=True)
    registers = Column(Integer, default=0)
    __tablename__ = "metrics"

    def __str__(self):
        return f'{self.fecha} {self.registers}'
