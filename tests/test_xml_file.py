import pytest

from execution.xml_file import XmlFile
from tests.cases import CASES

FIELDS = ('total', 'iva', 'ieps', 'ret_iva', 'ret_isr')


def _param(case):
    marks = [pytest.mark.xfail(reason=f'Fase 1: {case.phase1}', strict=True)] if case.phase1 else []
    return pytest.param(case, id=case.id, marks=marks)


@pytest.mark.parametrize('case', [_param(c) for c in CASES])
def test_parse_cfdi(case, xml_dir):
    xml = XmlFile(case.cfdi.write(xml_dir))

    assert xml.uuid == case.cfdi.uuid
    assert xml.emisor.rfc == case.cfdi.emisor_rfc
    assert xml.receptor.rfc == case.cfdi.receptor_rfc
    assert xml.date == case.cfdi.fecha
    assert xml.tipo == case.expected['tipo']
    assert {f: getattr(xml, f) for f in FIELDS} == {f: case.expected[f] for f in FIELDS}


@pytest.mark.parametrize('case_id, gravado, no_gravado', [
    ('v40_iva16', 1000, 0),
    ('v40_ieps_iva', 500, 200),          # el IEPS no se cuenta dos veces en el gravado
    ('v40_frontera_8', 1000, 0),
    ('v40_exento', 0, 1000),
    ('v40_descuento', 900, 0),
    ('v40_usd', 1750, 0),
    ('v33_iva16', 1000, 0),
    ('v32_iva16', 1000, 0),
])
def test_gravado_no_gravado(case_id, gravado, no_gravado, xml_dir):
    from tests.cases import CASES_BY_ID
    xml = XmlFile(CASES_BY_ID[case_id].cfdi.write(xml_dir))
    assert (xml.gravado, xml.no_gravado) == (gravado, no_gravado)


def test_bases_por_tasa(xml_dir):
    from tests.cases import CASES_BY_ID
    xml = XmlFile(CASES_BY_ID['v40_frontera_8'].cfdi.write(xml_dir))
    assert xml.bases['tasa8'] == 1000 and xml.bases['tasa16'] == 0


def test_no_es_cfdi(tmp_path):
    from exceptions import XmlDataException
    page = tmp_path / 'error.xml'
    page.write_text('<html><body>Error SAT</body></html>')
    with pytest.raises(XmlDataException):
        XmlFile(page)


def test_xxe_bloqueado(tmp_path):
    evil = tmp_path / 'evil.xml'
    evil.write_text('<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///c:/windows/win.ini">]>'
                    '<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Total="&x;"/>')
    with pytest.raises(Exception):
        XmlFile(evil).total
