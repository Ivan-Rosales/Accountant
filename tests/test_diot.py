from datetime import datetime
from decimal import Decimal as D

import pytest

from execution import diot
from execution.diot import DiotSettings, aggregate, export, line_2024, line_2025, sat_round, validate
from execution.xml_file import XmlFile
from tests.cases import CLIENTE_RFC, PROVEEDOR_RFC, PERSONA_FISICA_RFC, CASES_BY_ID
from tests.cfdi_builder import Cfdi, Concepto, Traslado, Retencion, IVA, ISR

ENERO = datetime(2025, 1, 10)


def compra(conceptos, emisor=PROVEEDOR_RFC, tipo='I', **kw):
    return Cfdi(emisor_rfc=emisor, receptor_rfc=CLIENTE_RFC, emisor_nombre='Proveedor', fecha=ENERO, tipo=tipo,
                conceptos=conceptos, **kw)


def parse(xml_dir, cfdis):
    return [XmlFile(c.write(xml_dir)) for c in cfdis]


@pytest.mark.parametrize('value, expected', [
    ('1450.50', 1450), ('1450.51', 1451), ('1450.49', 1450), ('0.50', 0), ('0.51', 1), ('1450.505', 1451),
])
def test_redondeo_art_20_cff(value, expected):
    assert sat_round(D(value)) == expected


def test_proveedor_nacional_16_con_nota_credito(xml_dir):
    files = parse(xml_dir, [compra([Concepto(1000)]), compra([Concepto(200)]), compra([Concepto(100)], tipo='E')])
    (p,) = aggregate(files)
    assert (p.rfc, p.tipo_tercero, p.tipo_operacion, p.documentos) == (PROVEEDOR_RFC, '04', '85', 3)
    row = line_2025(p)
    assert len(row) == 54
    assert row[:7] == ['04', '85', PROVEEDOR_RFC, '', '', '', '']
    assert (row[11], row[12], row[21]) == ('1200', '100', '176')  # valor 16, devoluciones, IVA (1100 x 16 %)
    assert row[53] == '01'
    assert validate(p, 2025) == []


def test_honorarios_sugiere_03_y_retenciones(xml_dir):
    honorarios = compra([Concepto(10000, retenciones=[Retencion(IVA, '0.106667'), Retencion(ISR, '0.100000')])],
                        emisor=PERSONA_FISICA_RFC)
    (p,) = aggregate(parse(xml_dir, [honorarios]))
    row = line_2025(p)
    assert (row[1], row[11], row[21], row[47]) == ('03', '10000', '1600', '1067')


def test_frontera_tasa0_exento_y_no_objeto(xml_dir):
    cfdi = compra([Concepto(1000, traslados=[Traslado(IVA, '0.080000')]),
                   Concepto(300, traslados=[Traslado(IVA, '0.000000')]),
                   Concepto(200, traslados=[Traslado(IVA, None)]),
                   Concepto(50, traslados=[])])
    (p,) = aggregate(parse(xml_dir, [cfdi]))
    row = line_2025(p)
    assert (row[7], row[17], row[11], row[49], row[50], row[51]) == ('1000', '80', '', '200', '300', '50')

    p.frontera = diot.FRONTERA_SUR
    row = line_2025(p)
    assert (row[7], row[9], row[17], row[19]) == ('', '1000', '', '80')


def test_ignora_nomina_pago_y_cancelados(xml_dir):
    nomina = Cfdi(emisor_rfc=CLIENTE_RFC, receptor_rfc=PERSONA_FISICA_RFC, tipo='N', fecha=ENERO,
                  conceptos=[Concepto(5000, traslados=[])])
    files = parse(xml_dir, [compra([Concepto(100)]), CASES_BY_ID['v40_pago'].cfdi, nomina])
    assert [p.rfc for p in aggregate(files)] == [PROVEEDOR_RFC]


def test_publico_en_general_es_global(xml_dir):
    (p,) = aggregate(parse(xml_dir, [compra([Concepto(100)], emisor='XAXX010101000')]))
    assert (p.tipo_tercero, p.tipo_operacion, line_2025(p)[2]) == ('15', '87', 'XAXX010101000')
    assert validate(p, 2025) == []


def test_ajustes_del_usuario(xml_dir):
    settings = {PROVEEDOR_RFC: DiotSettings(tipo_operacion='06', frontera='sur')}
    (p,) = aggregate(parse(xml_dir, [compra([Concepto(100)])]), settings)
    assert (p.tipo_operacion, p.frontera) == ('06', 'sur')


def test_extranjero_requiere_datos(xml_dir):
    (p,) = aggregate(parse(xml_dir, [compra([Concepto(100)], emisor='XEXX010101000')]))
    assert p.tipo_tercero == '05'
    assert len(validate(p, 2025)) >= 3
    p.apply(DiotSettings(tax_id='123456789', nombre_extranjero='ACME INC', pais='USA'))
    assert validate(p, 2025) == []
    assert line_2025(p)[:7] == ['05', '85', '', '123456789', 'ACME INC', 'USA', '']


def test_operacion_invalida_por_layout(xml_dir):
    (p,) = aggregate(parse(xml_dir, [compra([Concepto(100)])]))
    p.tipo_operacion = '02'  # enajenación existe solo desde 2025
    assert validate(p, 2025) == []
    assert validate(p, 2024)


def test_layout_2024(xml_dir):
    files = parse(xml_dir, [compra([Concepto(1000)]), compra([Concepto(100)], tipo='E'),
                            compra([Concepto(500, traslados=[Traslado(IVA, '0.080000')])])])
    (p,) = aggregate(files)
    row = line_2024(p, 2024)
    assert len(row) == 23
    assert (row[7], row[11], row[13], row[22]) == ('1000', '500', '', '16')
    assert line_2024(p, 2018)[11] == ''  # frontera norte vacía para 2018 y anteriores


def test_export_utf8_crlf(tmp_path, xml_dir):
    files = parse(xml_dir, [compra([Concepto(1000)]), compra([Concepto(10)], emisor='BBB030303CC1')])
    path = export(tmp_path / 'diot.txt', aggregate(files), 2025)
    data = path.read_bytes()
    assert not data.startswith(b'\xef\xbb\xbf')
    lines = data.decode('utf-8').split('\r\n')
    assert lines[-1] == '' and len(lines) == 3
    assert all(line.count('|') == 53 for line in lines[:-1])


def test_export_con_advertencias_genera_el_archivo(tmp_path, xml_dir):
    (p,) = aggregate(parse(xml_dir, [compra([Concepto(100)], emisor='XEXX010101000')]))
    issues = diot.summarize([p], 2025)[p.rfc]
    assert issues and all(i.level == diot.ADVERTENCIA for i in issues)
    path = export(tmp_path / 'diot.txt', [p], 2025)
    assert path.read_text(encoding='utf-8').startswith('05|85|')


def test_clave_no_reconocida_es_error_pero_exporta(tmp_path, xml_dir):
    (p,) = aggregate(parse(xml_dir, [compra([Concepto(100)])]))
    p.tipo_operacion = '99'
    (issue,) = diot.check(p, 2025)
    assert issue.level == diot.ERROR
    assert export(tmp_path / 'diot.txt', [p], 2025).exists()


def test_pipe_en_texto_se_reemplaza(xml_dir):
    (p,) = aggregate(parse(xml_dir, [compra([Concepto(100)], emisor='XEXX010101000')]))
    p.apply(DiotSettings(tax_id='12|3', nombre_extranjero='ACME', pais='USA'))
    (line,) = diot.build_lines([p], 2025)
    assert line.count('|') == 53 and '12 3' in line


def test_desde_registros_de_bd(tmp_path):
    from app.workers.database import database_worker
    from execution.month_process import process_folder
    from execution import cfdi_store
    from models import Cliente
    with database_worker.new_session() as session:
        client = Cliente(rfc=CLIENTE_RFC, nombre='C', apellido_paterno='', apellido_materno='')
        session.add(client)
        session.commit()
    folder = tmp_path / 'e'
    compra([Concepto(1000)]).write(folder)
    process_folder(client, folder)
    with database_worker.new_session() as session:
        records = cfdi_store.month_records(session, client, 2025, 1, False)
    (p,) = aggregate(records)
    assert line_2025(p)[11] == '1000'


def test_ajustes_se_guardan_por_cliente(tmp_path):
    from app.workers.database import database_worker
    from execution import cfdi_store
    from execution.month_process import process_folder
    from models import Cliente
    with database_worker.new_session() as session:
        client = Cliente(rfc=CLIENTE_RFC, nombre='C', apellido_paterno='', apellido_materno='')
        session.add(client)
        session.commit()
    compra([Concepto(1000)]).write(tmp_path / 'e')
    process_folder(client, tmp_path / 'e')

    with database_worker.new_session() as session:
        (p,) = aggregate(cfdi_store.received_records(session, client, 2025, 1))
        p.tipo_operacion, p.frontera = '06', 'sur'
        cfdi_store.save_diot_settings(session, client, [p])

    with database_worker.new_session() as session:
        settings = cfdi_store.diot_settings(session, client)
        (p,) = aggregate(cfdi_store.received_records(session, client, 2025, 1), settings)
    assert (p.tipo_operacion, p.frontera) == ('06', 'sur')
