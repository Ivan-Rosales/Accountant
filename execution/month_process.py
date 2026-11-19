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
                   create_providers=False) -> MonthResult:
    """Guarda en la BD los CFDI de la carpeta y regenera la hoja del mes con TODOS los CFDI
    guardados de ese mes y tipo (no solo los del ZIP actual), excluyendo los cancelados."""
    xml_files = MonthSummary.load_folder(folder)
    if not xml_files:
        raise ValidationException(f'No se encontraron archivos XML en {origen or folder}')

    MonthSummary(client).validate_batch(xml_files)
    reference = next((x for x in xml_files if x.tipo != 'N'), xml_files[0])
    year, month = reference.date.year, reference.date.month
    ingreso = reference.emisor.rfc == client.rfc

    with database_worker.new_session() as session:
        stats = cfdi_store.save_xml_files(session, client, xml_files, origen=origen)
        records = cfdi_store.month_records(session, client, year, month, ingreso)

    summary = MonthSummary(client)
    summary.add_records(records)
    summary.save()

    providers = None
    if create_providers:
        providers = MonthSummaryProviders(client)
        providers.add_records(records)
        providers.save()

    return MonthResult(summary, providers, stats['nuevos'], stats['actualizados'], len(records))
