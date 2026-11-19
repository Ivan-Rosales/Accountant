from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, UniqueConstraint, Index
from sqlalchemy.types import TypeDecorator

from app.workers.database import ModelMixin, DatabaseWorker


class Money(TypeDecorator):
    """Decimal guardado como texto: SQLite no tiene tipo decimal exacto y REAL perdería centavos."""
    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else str(Decimal(value))

    def process_result_value(self, value, dialect):
        return None if value is None else Decimal(value)


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

    def to_dict(self):
        return {'id': self.id, 'rfc': self.rfc, 'nombre': self.nombre, 'apellido_paterno': self.apellido_paterno,
                'apellido_materno': self.apellido_materno}


class Metrica(DatabaseWorker.base, ModelMixin):
    id = Column(Integer, primary_key=True)
    fecha = Column(Date, unique=True)
    registers = Column(Integer, default=0)
    __tablename__ = "metrics"

    def __str__(self):
        return f'{self.fecha} {self.registers}'


class Party:
    """Emisor o receptor de un comprobante guardado; misma interfaz que XmlNode."""

    def __init__(self, rfc, name):
        self.rfc = rfc or ''
        self.name = name or ''

    def __eq__(self, other):
        return self.rfc == other.rfc

    def __hash__(self):
        return hash(self.rfc)


class Comprobante(DatabaseWorker.base):
    """CFDI importado de un cliente. Importes en pesos, tal como los entrega XmlFile.

    Expone la misma interfaz que XmlFile (uuid, tipo, date, emisor, receptor, total, iva...) para
    que los concentrados se generen desde la base de datos sin volver a leer los XML.
    """
    __tablename__ = 'cfdi'
    __table_args__ = (
        UniqueConstraint('cliente_id', 'uuid', name='uq_cfdi_cliente_uuid'),
        Index('ix_cfdi_periodo', 'cliente_id', 'year', 'month', 'ingreso'),
    )

    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('client.id', ondelete='CASCADE'), nullable=False)
    uuid = Column(String(36), nullable=False)
    ingreso = Column(Boolean, nullable=False, comment='True si el cliente es el emisor')
    tipo = Column(String(1), nullable=False)
    version = Column(String(8))
    fecha = Column(DateTime, nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    emisor_rfc = Column(String(13))
    emisor_nombre = Column(String(300))
    receptor_rfc = Column(String(13))
    receptor_nombre = Column(String(300))

    moneda = Column(String(3))
    tipo_cambio = Column(Money)
    total = Column(Money, nullable=False)
    iva = Column(Money, nullable=False)
    ieps = Column(Money, nullable=False)
    ret_iva = Column(Money, nullable=False)
    ret_isr = Column(Money, nullable=False)
    gravado = Column(Money)
    no_gravado = Column(Money)
    base_tasa16 = Column(Money)
    base_tasa8 = Column(Money)
    base_tasa0 = Column(Money)
    base_exento = Column(Money)
    base_no_objeto = Column(Money)
    percepciones = Column(Money, comment='nómina: percepciones brutas')
    metodo_pago = Column(String(3), comment='PUE o PPD')

    cancelado = Column(Boolean, nullable=False, default=False)
    origen = Column(String(300), comment='archivo ZIP del que se importó')
    importado = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    @property
    def date(self):
        return self.fecha

    @property
    def emisor(self):
        return Party(self.emisor_rfc, self.emisor_nombre)

    @property
    def receptor(self):
        return Party(self.receptor_rfc, self.receptor_nombre)

    def __str__(self):
        return f'{self.uuid} {self.tipo} {self.fecha:%Y-%m-%d} {self.total}'


class ProveedorDiot(DatabaseWorker.base):
    """Datos de la DIOT que el XML no trae, capturados por cliente y proveedor."""
    __tablename__ = 'diot_proveedor'
    __table_args__ = (UniqueConstraint('cliente_id', 'rfc', name='uq_diot_cliente_rfc'),)

    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('client.id', ondelete='CASCADE'), nullable=False)
    rfc = Column(String(13), nullable=False)
    tipo_tercero = Column(String(2))
    tipo_operacion = Column(String(2))
    frontera = Column(String(5))
    tax_id = Column(String(40))
    nombre_extranjero = Column(String(300))
    pais = Column(String(3))
    jurisdiccion = Column(String(300))


class PagoDocumento(DatabaseWorker.base):
    """Pago aplicado a un documento, tomado del complemento de pagos (REP). Importes en pesos.

    Misma interfaz que Comprobante para la DIOT: tipo 'I', emisor, base_tasa16..., ret_iva, ret_isr.
    """
    __tablename__ = 'cfdi_pago'
    __table_args__ = (Index('ix_pago_periodo', 'cliente_id', 'year', 'month', 'ingreso'),)

    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('client.id', ondelete='CASCADE'), nullable=False)
    pago_uuid = Column(String(36), nullable=False, index=True, comment='UUID del CFDI de pago')
    documento_uuid = Column(String(36), nullable=False, index=True, comment='UUID de la factura pagada')
    ingreso = Column(Boolean, nullable=False)
    fecha_pago = Column(DateTime, nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    emisor_rfc = Column(String(13))
    emisor_nombre = Column(String(300))

    imp_pagado = Column(Money, nullable=False)
    con_impuestos = Column(Boolean, nullable=False, default=False, comment='trae ImpuestosDR (Pagos 2.0)')
    base_tasa16 = Column(Money)
    base_tasa8 = Column(Money)
    base_tasa0 = Column(Money)
    base_exento = Column(Money)
    base_no_objeto = Column(Money)
    iva = Column(Money)
    ret_iva = Column(Money)
    ret_isr = Column(Money)

    tipo = 'I'
    cancelado = False
    aviso = None

    @property
    def emisor(self):
        return Party(self.emisor_rfc, self.emisor_nombre)
