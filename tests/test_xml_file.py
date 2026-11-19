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
