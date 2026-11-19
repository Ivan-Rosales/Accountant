"""Flujo del concentrado mensual: XML -> base de datos -> Excel."""
from dataclasses import dataclass
from pathlib import Path

from app.workers.database import database_worker
from exceptions import ValidationException
from execution import cfdi_store
from execution.month_summary import MonthSummary
from execution.month_summary_providers import MonthSummaryProviders
from models import Cliente


@dataclass
class MonthResult:
    summary: MonthSummary
    providers: MonthSummaryProviders | None
    nuevos: int
    actualizados: int
    total_mes: int


def process_folder(client: Cliente, folder: Path, origen: str | None = None,
                   create_providers=False, nomina_importe=None) -> MonthResult:
    """Guarda en la BD los CFDI de la carpeta y regenera la hoja del mes con TODOS los CFDI
    guardados de ese mes y tipo (no solo los del ZIP actual), excluyendo los cancelados."""
    xml_files = MonthSummary.load_folder(folder)
    if not xml_files:
        raise ValidationException(f'No se encontraron archivos XML en {origen or folder}')

    checker = MonthSummary(client)
    checker.validate_batch(xml_files)
    no_nomina = [x for x in xml_files if x.tipo not in ('N', 'P')]
    reference = (no_nomina or xml_files)[0]
    year, month = reference.date.year, reference.date.month
    ingreso = checker.detect_rev(xml_files)

    # Periodos afectados: el del ZIP y, si trae nóminas del cliente, los egresos del mes de cada nómina
    periods = {(year, month, ingreso)}
    periods |= {(x.date.year, x.date.month, False) for x in xml_files if checker.is_nomina_emitida(x)}

    with database_worker.new_session() as session:
        stats = cfdi_store.save_xml_files(session, client, xml_files, origen=origen)
        records = {p: cfdi_store.month_records(session, client, *p) for p in periods}

    def build(cls, period):
        summary = cls(client, nomina_importe=nomina_importe)
        summary.add_records(records[period])
        summary.save()
        return summary

    main = (year, month, ingreso)
    summary = build(MonthSummary, main)
    for period in periods - {main}:
        if records[period]: build(MonthSummary, period)

    providers = build(MonthSummaryProviders, main) if create_providers else None
    return MonthResult(summary, providers, stats['nuevos'], stats['actualizados'], len(records[main]))
