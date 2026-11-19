"""Archivo de carga masiva DIOT (SAT), layouts 2025+ (54 campos) y 2024 y anteriores (23 campos).

Fuente: "Instructivo para el armado del archivo de carga masiva DIOT REV-2" del SAT.

- Una línea por tercero (proveedor) y tipo de operación; campos separados por "|", sin encabezado.
- Montos en pesos, enteros, sin decimales ni separadores; redondeo del art. 20 CFF
  (.01-.50 baja, .51-.99 sube).
- Archivo .txt en UTF-8 sin BOM.

Los montos se calculan con los CFDI RECIBIDOS del periodo (base: fecha de la factura). La DIOT
pide lo efectivamente pagado: para facturas PPD habría que usar los complementos de pago.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_DOWN, ROUND_HALF_UP
from pathlib import Path
import re

ZERO = Decimal(0)
TASA16, TASA8 = Decimal('0.16'), Decimal('0.08')

NACIONAL, EXTRANJERO, GLOBAL = '04', '05', '15'
TIPOS_TERCERO = {NACIONAL: 'Nacional', EXTRANJERO: 'Extranjero', GLOBAL: 'Global'}

TIPOS_OPERACION = {
    '02': 'Enajenación de bienes',
    '03': 'Servicios profesionales',
    '06': 'Uso o goce temporal de bienes',
    '07': 'Importación de bienes o servicios',
    '08': 'Importación por transferencia virtual',
    '85': 'Otros',
    '87': 'Operaciones globales',
}
OPERACIONES_2025 = {NACIONAL: {'02', '03', '06', '08', '85'}, EXTRANJERO: {'02', '03', '07', '85'}, GLOBAL: {'87'}}
OPERACIONES_2024 = {NACIONAL: {'03', '06', '85'}, EXTRANJERO: {'03', '85'}, GLOBAL: {'87'}}

FRONTERA_NORTE, FRONTERA_SUR = 'norte', 'sur'
RFC_GLOBAL = 'XAXX010101000'
RFC_EXTRANJERO = 'XEXX010101000'
RFC_PATTERN = re.compile(r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$')
TEXT_PATTERN = re.compile(r'^[A-Za-z0-9 @´%#¡!.,$&¿?ñÑ/\-_Ü]*$')

FIELDS_2025 = 54
FIELDS_2024 = 23


def sat_round(value: Decimal) -> int:
    """Redondeo a pesos del art. 20 CFF: de .01 a .50 baja, de .51 a .99 sube."""
    cents = Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return int(cents.quantize(Decimal('1'), rounding=ROUND_HALF_DOWN))


def amount(value) -> str:
    """Monto para el archivo: entero o vacío si es cero."""
    number = sat_round(value or ZERO)
    return '' if number == 0 else str(number)


@dataclass
class DiotSettings:
    """Datos que el XML no trae y el usuario captura por proveedor (se guardan por cliente)."""
    tipo_tercero: str | None = None
    tipo_operacion: str | None = None
    frontera: str = FRONTERA_NORTE
    tax_id: str = ''
    nombre_extranjero: str = ''
    pais: str = ''
    jurisdiccion: str = ''


@dataclass
class DiotProvider:
    rfc: str
    nombre: str = ''
    tipo_tercero: str = NACIONAL
    tipo_operacion: str = '85'
    frontera: str = FRONTERA_NORTE
    tax_id: str = ''
    nombre_extranjero: str = ''
    pais: str = ''
    jurisdiccion: str = ''

    documentos: int = 0
    base16: Decimal = ZERO
    dev16: Decimal = ZERO
    base8: Decimal = ZERO
    dev8: Decimal = ZERO
    tasa0: Decimal = ZERO
    exento: Decimal = ZERO
    no_objeto: Decimal = ZERO
    iva_retenido: Decimal = ZERO
    ret_isr: Decimal = ZERO
    warnings: list = field(default_factory=list)

    # IVA pagado calculado sobre la base neta de devoluciones, para que nunca exceda base x tasa
    @property
    def iva16(self):
        return (self.base16 - self.dev16) * TASA16

    @property
    def iva8(self):
        return (self.base8 - self.dev8) * TASA8

    @property
    def iva_devoluciones(self):
        return self.dev16 * TASA16 + self.dev8 * TASA8

    @property
    def total(self):
        return self.base16 - self.dev16 + self.base8 - self.dev8 + self.tasa0 + self.exento + self.no_objeto

    def apply(self, settings: DiotSettings | None):
        if settings is None: return
        for key in ('tipo_tercero', 'tipo_operacion', 'frontera', 'tax_id', 'nombre_extranjero', 'pais',
                    'jurisdiccion'):
            value = getattr(settings, key)
            if value: setattr(self, key, value)


def suggest_tercero(rfc: str) -> str:
    if rfc == RFC_GLOBAL: return GLOBAL
    if rfc == RFC_EXTRANJERO: return EXTRANJERO
    return NACIONAL


def suggest_operacion(provider: DiotProvider) -> str:
    """Sugerencia; el usuario la confirma. Honorarios (persona física con retención de ISR) = 03."""
    if provider.tipo_tercero == GLOBAL: return '87'
    if provider.ret_isr > 0 and len(provider.rfc) == 13: return '03'
    return '85'


def aggregate(records, settings: dict[str, DiotSettings] | None = None) -> list[DiotProvider]:
    """Agrupa los CFDI recibidos por proveedor (RFC del emisor).

    `records` son Comprobante o XmlFile de egresos. Se ignoran nóminas (N), pagos (P),
    traslados (T) y cancelados. Las notas de crédito (E) se registran como devoluciones.
    """
    settings = settings or {}
    providers: dict[str, DiotProvider] = {}

    for r in records:
        if r.tipo not in ('I', 'E') or getattr(r, 'cancelado', False):
            continue
        rfc = (r.emisor.rfc or '').upper()
        p = providers.get(rfc)
        if p is None:
            p = providers[rfc] = DiotProvider(rfc=rfc, nombre=r.emisor.name or '', tipo_tercero=suggest_tercero(rfc))

        base = getattr(r, 'bases', None) or {
            'tasa16': r.base_tasa16, 'tasa8': r.base_tasa8, 'tasa0': r.base_tasa0,
            'exento': r.base_exento, 'no_objeto': r.base_no_objeto,
        }
        base = {k: Decimal(v or 0) for k, v in base.items()}
        p.documentos += 1
        if aviso := getattr(r, 'aviso', None):
            p.warnings.append(aviso)

        if r.tipo == 'E':
            p.dev16 += base['tasa16']
            p.dev8 += base['tasa8']
            # Devoluciones de actos a tasa 0 / exentos / no objeto disminuyen esos valores
            p.tasa0 -= base['tasa0']
            p.exento -= base['exento']
            p.no_objeto -= base['no_objeto']
            p.iva_retenido -= Decimal(r.ret_iva or 0)
            p.ret_isr -= Decimal(r.ret_isr or 0)
        else:
            p.base16 += base['tasa16']
            p.base8 += base['tasa8']
            p.tasa0 += base['tasa0']
            p.exento += base['exento']
            p.no_objeto += base['no_objeto']
            p.iva_retenido += Decimal(r.ret_iva or 0)
            p.ret_isr += Decimal(r.ret_isr or 0)

    result = []
    for p in providers.values():
        p.tipo_operacion = suggest_operacion(p)
        p.apply(settings.get(p.rfc))
        result.append(p)
    return sorted(result, key=lambda p: (p.tipo_tercero, p.nombre, p.rfc))


def _tercero_fields(p: DiotProvider) -> list[str]:
    extranjero = p.tipo_tercero == EXTRANJERO
    rfc = RFC_GLOBAL if p.tipo_tercero == GLOBAL else ('' if extranjero and p.rfc == RFC_EXTRANJERO else p.rfc)
    return [
        p.tipo_tercero,
        p.tipo_operacion,
        rfc,
        p.tax_id if extranjero else '',
        p.nombre_extranjero if extranjero else '',
        p.pais.upper() if extranjero else '',
        p.jurisdiccion if extranjero and p.pais.upper() == 'ZZZ' else '',
    ]


def line_2025(p: DiotProvider, efectos_fiscales='01') -> list[str]:
    norte = p.frontera == FRONTERA_NORTE
    row = [''] * FIELDS_2025
    row[0:7] = _tercero_fields(p)
    # Valor de actos o actividades (sin IVA)
    row[7] = amount(p.base8) if norte else ''          # 8  frontera norte
    row[8] = amount(p.dev8) if norte else ''           # 9  devoluciones frontera norte
    row[9] = '' if norte else amount(p.base8)          # 10 frontera sur
    row[10] = '' if norte else amount(p.dev8)          # 11 devoluciones frontera sur
    row[11] = amount(p.base16)                         # 12 tasa 16 %
    row[12] = amount(p.dev16)                          # 13 devoluciones 16 %
    # IVA acreditable: por defecto todo "exclusivamente de actividades gravadas"
    if sat_round(p.base8) > 0:
        row[17 if norte else 19] = amount(p.iva8)      # 18 / 20
    if sat_round(p.base16) > 0:
        row[21] = amount(p.iva16)                      # 22
    # Datos adicionales
    row[47] = amount(p.iva_retenido)                   # 48 IVA retenido
    row[49] = amount(p.exento)                         # 50 exentos
    row[50] = amount(p.tasa0)                          # 51 tasa 0 %
    row[51] = amount(p.no_objeto)                      # 52 no objeto
    row[53] = efectos_fiscales                         # 54 se dio efectos fiscales
    return row


def line_2024(p: DiotProvider, year: int) -> list[str]:
    norte = p.frontera == FRONTERA_NORTE
    row = [''] * FIELDS_2024
    row[0:7] = _tercero_fields(p)
    row[7] = amount(p.base16)                                   # 8  actos al 16 %
    if norte and year >= 2019: row[11] = amount(p.base8)        # 12 frontera norte
    if not norte and year >= 2021: row[13] = amount(p.base8)    # 14 frontera sur
    row[18] = amount(p.exento)                                  # 19 exentos
    row[19] = amount(p.tasa0)                                   # 20 tasa 0 %
    row[20] = amount(p.no_objeto)                               # 21 no objeto
    row[21] = amount(p.iva_retenido)                            # 22 IVA retenido
    row[22] = amount(p.iva_devoluciones)                        # 23 IVA de devoluciones
    return row


def validate(p: DiotProvider, year: int) -> list[str]:
    """Reglas del instructivo que causan rechazo. Devuelve los errores encontrados."""
    errors = []
    operaciones = (OPERACIONES_2025 if year >= 2025 else OPERACIONES_2024).get(p.tipo_tercero)
    if operaciones is None:
        errors.append(f'Tipo de tercero inválido: {p.tipo_tercero}')
    elif p.tipo_operacion not in operaciones:
        errors.append(f'El tipo de operación {p.tipo_operacion} no aplica a un tercero '
                      f'{TIPOS_TERCERO[p.tipo_tercero].lower()} en {year}')

    if p.tipo_tercero == NACIONAL:
        if not RFC_PATTERN.match(p.rfc) or p.rfc in (RFC_GLOBAL, RFC_EXTRANJERO):
            errors.append(f'RFC inválido para tercero nacional: {p.rfc}')
    elif p.tipo_tercero == EXTRANJERO:
        if not p.tax_id: errors.append('Falta el número de identificación fiscal del extranjero')
        if not p.nombre_extranjero: errors.append('Falta el nombre del extranjero')
        if not re.fullmatch(r'[A-Z]{3}', p.pais.upper()): errors.append('Falta el país (clave de 3 letras)')
        if p.pais.upper() == 'ZZZ' and not p.jurisdiccion: errors.append('País ZZZ requiere lugar de jurisdicción')
        for text in (p.tax_id, p.nombre_extranjero, p.jurisdiccion):
            if text and not TEXT_PATTERN.match(text): errors.append(f'Caracteres no permitidos: {text}')
        if len(p.tax_id) > 40: errors.append('Identificación fiscal mayor a 40 caracteres')

    if p.dev16 > p.base16: errors.append('Las devoluciones al 16 % exceden el valor de los actos')
    if p.dev8 > p.base8: errors.append('Las devoluciones en región fronteriza exceden el valor de los actos')
    for name in ('tasa0', 'exento', 'no_objeto', 'iva_retenido'):
        if getattr(p, name) < 0: errors.append(f'El valor de {name} queda negativo (más devoluciones que compras)')
    if p.frontera not in (FRONTERA_NORTE, FRONTERA_SUR): errors.append(f'Región fronteriza inválida: {p.frontera}')
    return errors


def build_lines(providers, year: int, efectos_fiscales='01') -> list[str]:
    lines = []
    for p in providers:
        row = line_2025(p, efectos_fiscales) if year >= 2025 else line_2024(p, year)
        for value in row:
            if '|' in value:
                raise ValueError(f'El valor contiene "|": {value}')
        lines.append('|'.join(row))
    return lines


def export(path: Path, providers, year: int, efectos_fiscales='01') -> Path:
    """Escribe el TXT. Lanza ValueError si algún proveedor tiene errores de validación."""
    providers = [p for p in providers if p.documentos]
    errors = {p.rfc: e for p in providers if (e := validate(p, year))}
    if errors:
        detail = '\n'.join(f'{rfc}: {"; ".join(e)}' for rfc, e in errors.items())
        raise ValueError(f'Hay proveedores con errores:\n{detail}')

    path.parent.mkdir(parents=True, exist_ok=True)
    content = '\r\n'.join(build_lines(providers, year, efectos_fiscales))
    path.write_bytes((content + '\r\n').encode('utf-8') if content else b'')
    return path


def default_filename(workdir: Path, rfc: str, year: int, month: int) -> Path:
    return Path(workdir) / rfc / 'DIOT' / f'{rfc} {year} {month:02d} DIOT.txt'
