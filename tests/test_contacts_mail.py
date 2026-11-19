from datetime import datetime

import pytest

from app.workers.database import database_worker
from execution import contacts as store, mailer
from models import Cliente, Contacto
from tests.cases import CLIENTE_RFC, PROVEEDOR_RFC
from tests.cfdi_builder import Cfdi, Concepto

ENERO = datetime(2025, 1, 10)


@pytest.fixture
def client():
    with database_worker.new_session() as session:
        c = Cliente(rfc=CLIENTE_RFC, nombre='MI', apellido_paterno='CLIENTE', apellido_materno='SA')
        session.add(c)
        session.commit()
        return c


@pytest.fixture
def session():
    with database_worker.new_session() as s:
        yield s


def invoice(folder, name='F-001', emisor=CLIENTE_RFC, receptor=PROVEEDOR_RFC, pdf=True):
    cfdi = Cfdi(emisor_rfc=emisor, emisor_nombre='Mi Cliente SA', receptor_rfc=receptor,
                receptor_nombre='Comprador SA', fecha=ENERO, conceptos=[Concepto(1000)])
    xml = cfdi.write(folder, name)
    if pdf: (folder / f'{name}.pdf').write_bytes(b'%PDF-1.4 prueba')
    return cfdi, xml


# ---- contactos -------------------------------------------------------------------
def test_contactos_y_correos(client, session):
    contact = store.save_contact(session, client, 'bbb020202bbb', 'Comprador SA')
    assert contact.rfc == PROVEEDOR_RFC
    invalid = store.add_emails(session, contact.id, store.split_emails('A@x.com; b@y.mx, malo, a@x.com'))
    assert invalid == ['malo']
    (view,) = store.list_contacts(session, client)
    assert view.emails == ['a@x.com', 'b@y.mx']

    store.remove_emails(session, contact.id, ['a@x.com'])
    assert store.list_contacts(session, client)[0].emails == ['b@y.mx']

    with pytest.raises(ValueError, match='Ya existe'):
        store.save_contact(session, client, PROVEEDOR_RFC, 'Otro')
    with pytest.raises(ValueError, match='RFC'):
        store.save_contact(session, client, 'CORTO', 'X')

    store.delete_contacts(session, [contact.id])
    assert store.list_contacts(session, client) == []


def test_borrar_cliente_borra_sus_contactos(client, session):
    contact = store.save_contact(session, client, PROVEEDOR_RFC, 'Comprador')
    store.add_emails(session, contact.id, ['a@x.com'])
    session.delete(session.get(Cliente, client.id))
    session.commit()
    assert session.query(Contacto).count() == 0


# ---- pares y análisis ---------------------------------------------------------------
def test_pares_xml_pdf(tmp_path):
    invoice(tmp_path, 'A')
    invoice(tmp_path, 'B', pdf=False)
    (tmp_path / 'C.PDF').write_bytes(b'x')
    (tmp_path / 'c.xml').write_text('<x/>')
    names = sorted(x.stem for x, _ in mailer.find_pairs(tmp_path))
    assert names == ['A', 'c']
    assert mailer.pair_for(tmp_path / 'A.pdf')[0].name == 'A.xml'
    assert mailer.pair_for(tmp_path / 'B.xml') is None


def test_ignora_xml_que_no_es_factura(tmp_path, session):
    (tmp_path / 'basura.xml').write_text('<html>Error SAT</html>')
    (tmp_path / 'basura.pdf').write_bytes(b'x')
    (tmp_path / 'roto.xml').write_text('<<no es xml')
    (tmp_path / 'roto.pdf').write_bytes(b'x')
    assert mailer.scan(session, tmp_path) == []


def test_recomienda_correos_del_contacto(tmp_path, client, session):
    otro = store.save_contact(session, client, 'CCC030303CC1', 'Otro cliente')
    store.add_emails(session, otro.id, ['otro@x.com'])
    comprador = store.save_contact(session, client, PROVEEDOR_RFC, 'Comprador')
    store.add_emails(session, comprador.id, ['compras@comprador.com'])
    cfdi, xml = invoice(tmp_path)

    (mail,) = mailer.scan(session, tmp_path)
    assert (mail.cliente_id, mail.contacto_rfc, mail.contact_exists) == (client.id, PROVEEDOR_RFC, True)
    assert mail.recommended == ['compras@comprador.com']
    assert sorted(e for emails in mail.all_emails.values() for e in emails) == ['compras@comprador.com', 'otro@x.com']


def test_contacto_nuevo_se_guarda(tmp_path, client, session):
    invoice(tmp_path)
    (mail,) = mailer.scan(session, tmp_path)
    assert (mail.contact_exists, mail.recommended) == (False, [])
    store.upsert_contact_with_emails(session, client, mail.contacto_rfc, mail.contacto_nombre, ['nuevo@x.com'])
    (mail,) = mailer.scan(session, tmp_path)
    assert mail.recommended == ['nuevo@x.com']


def test_cliente_como_receptor(tmp_path, client, session):
    invoice(tmp_path, emisor=PROVEEDOR_RFC, receptor=CLIENTE_RFC)
    (mail,) = mailer.scan(session, tmp_path)
    assert (mail.cliente_id, mail.contacto_rfc) == (client.id, PROVEEDOR_RFC)


def test_cliente_no_registrado(tmp_path, session):
    invoice(tmp_path, emisor='ZZZ010101ZZZ')
    (mail,) = mailer.scan(session, tmp_path)
    assert mail.cliente_id is None


# ---- envío ------------------------------------------------------------------------
class FakeSMTP:
    sent = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port = host, port

    def starttls(self, context=None): pass

    def login(self, user, password):
        if password != 'secreta': raise mailer.smtplib.SMTPAuthenticationError(535, b'bad')

    def send_message(self, message): FakeSMTP.sent.append(message)

    def quit(self): pass


SMTP = mailer.SmtpSettings(host='smtp.test', port=465, security='ssl', user='yo@test.com', from_name='Despacho')


def test_envio_y_historial(tmp_path, client, session, monkeypatch):
    monkeypatch.setattr(mailer.smtplib, 'SMTP_SSL', FakeSMTP)
    FakeSMTP.sent = []
    invoice(tmp_path)
    (mail,) = mailer.scan(session, tmp_path)

    row = mailer.send_invoice(session, SMTP, 'secreta', mail, ['A@X.com'], mailer.default_subject(mail),
                              mailer.default_body(mail))
    assert row.estado == 'enviado' and row.destinatarios == 'a@x.com'
    (message,) = FakeSMTP.sent
    assert message['To'] == 'a@x.com' and 'Despacho' in message['From']
    assert sorted(p.get_filename() for p in message.iter_attachments()) == ['F-001.pdf', 'F-001.xml']

    (mail,) = mailer.scan(session, tmp_path)
    assert len(mail.sent_before) == 1


def test_error_de_envio_se_registra(tmp_path, client, session, monkeypatch):
    monkeypatch.setattr(mailer.smtplib, 'SMTP_SSL', FakeSMTP)
    invoice(tmp_path)
    (mail,) = mailer.scan(session, tmp_path)
    with pytest.raises(mailer.smtplib.SMTPAuthenticationError):
        mailer.send_invoice(session, SMTP, 'mala', mail, ['a@x.com'], 's', 'b')
    (row,) = mailer.history(session)
    assert row.estado == 'error'


def test_valida_destinatarios(tmp_path, client, session):
    invoice(tmp_path)
    (mail,) = mailer.scan(session, tmp_path)
    with pytest.raises(ValueError, match='no válidos'):
        mailer.send_invoice(session, SMTP, 'secreta', mail, ['malo'], 's', 'b')
    with pytest.raises(ValueError, match='destinatario'):
        mailer.send_invoice(session, SMTP, 'secreta', mail, [], 's', 'b')
