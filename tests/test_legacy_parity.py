"""Compara el parser nuevo contra el del programa anterior (Tkinter, DocXML).

Se salta si el programa anterior no está en la máquina. Rutas configurables:
  ACCOUNTANT_LEGACY_DIR   carpeta del programa anterior (DocXML.py)
  ACCOUNTANT_REAL_CFDI_DIR carpeta opcional con XML reales (NO se versionan) para comparar también
"""
import importlib
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from execution.xml_file import XmlFile
from tests.cases import CASES

LEGACY_DIR = Path(os.getenv('ACCOUNTANT_LEGACY_DIR', r'C:\Users\rosma\OneDrive\Documentos\Files\Programa Conta'))
REAL_DIR = os.getenv('ACCOUNTANT_REAL_CFDI_DIR')

FIELDS = {
    'total': ('getTotal', 'total'),
    'iva': ('getIva', 'iva'),
    'ieps': ('getIeps', 'ieps'),
    'ret_iva': ('RetIva', 'ret_iva'),
    'ret_isr': ('RetIsr', 'ret_isr'),
}

pytestmark = pytest.mark.skipif(not (LEGACY_DIR / 'DocXML.py').exists(),
                                reason=f'Programa anterior no encontrado en {LEGACY_DIR}')


@pytest.fixture(scope='module')
def legacy():
    sys.path.insert(0, str(LEGACY_DIR))
    try:
        yield importlib.import_module('DocXML').DocXML
    finally:
        sys.path.remove(str(LEGACY_DIR))


def legacy_values(DocXML, path: Path):
    doc = DocXML(path.read_text(encoding='utf-8-sig'), path.name).getFac()
    values = {k: Decimal(str(getattr(doc, old)())).quantize(Decimal('0.01')) for k, (old, _) in FIELDS.items()}
    values |= {'rfc_emisor': doc.getRfcE(), 'rfc_receptor': doc.getRfcR()}
    return values


def new_values(path: Path):
    xml = XmlFile(path)
    values = {k: getattr(xml, new) for k, (_, new) in FIELDS.items()}
    values |= {'rfc_emisor': xml.emisor.rfc, 'rfc_receptor': xml.receptor.rfc}
    return values


def _param(case):
    marks = []
    if case.phase1:
        marks.append(pytest.mark.xfail(reason=f'Fase 1: {case.phase1}', strict=True))
    elif case.cfdi.tipo in ('P', 'N'):
        marks.append(pytest.mark.skip(reason='El programa anterior no expone totales de pago/nómina por DocXML'))
    return pytest.param(case, id=case.id, marks=marks)


@pytest.mark.parametrize('case', [_param(c) for c in CASES if c.legacy_ok])
def test_parser_igual_al_anterior(case, legacy, xml_dir):
    path = case.cfdi.write(xml_dir)
    assert new_values(path) == legacy_values(legacy, path)


def _real_files():
    if not REAL_DIR: return []
    return sorted(Path(REAL_DIR).glob('*.xml'))


@pytest.mark.skipif(not REAL_DIR, reason='Defina ACCOUNTANT_REAL_CFDI_DIR para comparar XML reales')
@pytest.mark.parametrize('path', _real_files(), ids=lambda p: p.name)
def test_parser_igual_al_anterior_xml_reales(path, legacy):
    assert new_values(path) == legacy_values(legacy, path)
