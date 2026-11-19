"""Envío de facturas por correo: pares PDF+XML, destinatarios sugeridos, SMTP e historial.

- Un "par" es un .xml y un .pdf con el mismo nombre en la misma carpeta.
- Si el XML no es un CFDI o no se puede leer, el par se ignora en silencio.
- Cliente: el que emite la factura (o, si no, el que la recibe). Contacto: la otra parte (por RFC).
- La contraseña SMTP vive en el Administrador de credenciales de Windows (keyring), nunca en conf.ini.
"""
import mimetypes
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from execution import contacts as contact_store
from execution.xml_file import XmlFile
from logger import logger
from models import Cliente, EnvioCorreo

KEYRING_SERVICE = 'Accountant SMTP'
SECURITY_SSL, SECURITY_STARTTLS, SECURITY_NONE = 'ssl', 'starttls', 'none'
SECURITIES = {SECURITY_SSL: 'SSL (puerto 465)', SECURITY_STARTTLS: 'STARTTLS (puerto 587)', SECURITY_NONE: 'Sin cifrado'}
TIPOS = {'I': 'Factura', 'E': 'Nota de crédito', 'P': 'Complemento de pago', 'N': 'Recibo de nómina',
         'T': 'Carta porte'}


# ---- pares de archivos --------------------------------------------------------
def find_pairs(folder: Path) -> list[tuple[Path, Path]]:
    """[(xml, pdf)] de la carpeta (sin subcarpetas) con el mismo nombre, sin importar mayúsculas."""
    folder = Path(folder)
    if not folder.is_dir(): return []
    files = {}
    for path in folder.iterdir():
        if path.is_file() and path.suffix.lower() in ('.xml', '.pdf'):
            files.setdefault(path.stem.lower(), {})[path.suffix.lower()] = path
    return sorted(((f['.xml'], f['.pdf']) for f in files.values() if '.xml' in f and '.pdf' in f),
                  key=lambda pair: pair[0].stat().st_mtime, reverse=True)


def pair_for(path: Path) -> tuple[Path, Path] | None:
    """El par al que pertenece un archivo (xml o pdf), si su compañero ya existe."""
    path = Path(path)
    if path.suffix.lower() not in ('.xml', '.pdf'): return None
    for pair in find_pairs(path.parent):
        if path.stem.lower() == pair[0].stem.lower():
            return pair
    return None


# ---- análisis de la factura ------------------------------------------------------
@dataclass
class InvoiceMail:
    xml_path: Path
    pdf_path: Path
    uuid: str
    tipo: str
    fecha: datetime
    total: object
    serie_folio: str
    emisor_rfc: str
    emisor_nombre: str
    cliente_id: int | None
    cliente_rfc: str
    cliente_nombre: str
    contacto_rfc: str
    contacto_nombre: str
    recommended: list = field(default_factory=list)       # correos del contacto
    all_emails: dict = field(default_factory=dict)        # {'(RFC) nombre': [correos]} de todo el cliente
    contact_exists: bool = False
    sent_before: list = field(default_factory=list)       # envíos previos de este UUID

    @property
    def key(self):
        return str(self.xml_path).lower()

    @property
    def label(self):
        return f'{TIPOS.get(self.tipo, "CFDI")} {self.serie_folio}'.strip()


def analyze(session: Session, xml_path: Path, pdf_path: Path) -> InvoiceMail | None:
    """Lee el XML y arma los datos del correo. None si no es un CFDI legible (se ignora)."""
    try:
        xml = XmlFile(xml_path)
        uuid, emisor, receptor = xml.uuid, xml.emisor, xml.receptor
        fecha, total, tipo = xml.date, xml.total, xml.tipo
    except Exception as error:
        logger.debug(f'Correo: se ignora {xml_path.name}: {error}')
        return None

    clients = {c.rfc.upper(): c for c in session.scalars(select(Cliente))}
    client = clients.get(emisor.rfc)
    counterpart = receptor
    if client is None and receptor.rfc in clients:
        client, counterpart = clients[receptor.rfc], emisor

    mail = InvoiceMail(
        xml_path=Path(xml_path), pdf_path=Path(pdf_path), uuid=uuid, tipo=tipo, fecha=fecha, total=total,
        serie_folio=f'{xml.serie}{xml.folio}' or uuid.split('-')[-1], emisor_rfc=emisor.rfc,
        emisor_nombre=emisor.name, cliente_id=client.id if client else None,
        cliente_rfc=client.rfc if client else '', cliente_nombre=client.fullname() if client else '',
        contacto_rfc=counterpart.rfc, contacto_nombre=counterpart.name,
    )
    if client is not None:
        for contact in contact_store.list_contacts(session, client):
            if contact.emails:
                mail.all_emails[str(contact)] = contact.emails
            if contact.rfc == counterpart.rfc:
                mail.contact_exists = True
                mail.recommended = list(contact.emails)
    mail.sent_before = list(session.scalars(select(EnvioCorreo).where(
        EnvioCorreo.uuid == uuid, EnvioCorreo.estado == 'enviado').order_by(EnvioCorreo.fecha.desc())))
    return mail


def scan(session: Session, folder: Path) -> list[InvoiceMail]:
    return [mail for xml, pdf in find_pairs(folder) if (mail := analyze(session, xml, pdf)) is not None]


# ---- mensaje ------------------------------------------------------------------
def default_subject(mail: InvoiceMail) -> str:
    return f'{mail.label} - {mail.emisor_nombre or mail.emisor_rfc}'


def default_body(mail: InvoiceMail) -> str:
    return (f'Estimado(a) {mail.contacto_nombre or "cliente"}:\n\n'
            f'Le hacemos llegar el comprobante fiscal {mail.label} con fecha {mail.fecha:%d/%m/%Y} '
            f'por un total de ${mail.total:,.2f}.\n\n'
            f'Se adjuntan los archivos PDF y XML.\n\nSaludos cordiales.\n{mail.emisor_nombre}')


@dataclass
class SmtpSettings:
    host: str
    port: int
    security: str
    user: str
    from_name: str = ''

    @classmethod
    def from_settings(cls, settings) -> 'SmtpSettings':
        def get(key, default=''):
            value = settings.value(key)
            return default if value in (None, '') else value

        security = get('mail-security', SECURITY_SSL)
        port = get('mail-port', 465 if security == SECURITY_SSL else 587)
        return cls(host=str(get('mail-host')), port=int(port), security=security, user=str(get('mail-user')),
                   from_name=str(get('mail-from-name')))

    def validate(self):
        if not self.host or not self.user:
            raise ValueError('Configure el servidor SMTP y el usuario en Configuración > Correo')


def get_password(user: str) -> str | None:
    import keyring
    return keyring.get_password(KEYRING_SERVICE, user) if user else None


def set_password(user: str, password: str):
    import keyring
    keyring.set_password(KEYRING_SERVICE, user, password)


def build_message(smtp: SmtpSettings, recipients: list[str], subject: str, body: str,
                  attachments: list[Path]) -> EmailMessage:
    message = EmailMessage()
    message['From'] = formataddr((smtp.from_name, smtp.user)) if smtp.from_name else smtp.user
    message['To'] = ', '.join(recipients)
    message['Subject'] = subject
    message['Message-ID'] = make_msgid()
    message.set_content(body)
    for path in attachments:
        ctype, _ = mimetypes.guess_type(path.name)
        maintype, subtype = (ctype or 'application/octet-stream').split('/', 1)
        message.add_attachment(Path(path).read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)
    return message


def connect(smtp: SmtpSettings, password: str, timeout=30):
    context = ssl.create_default_context()
    if smtp.security == SECURITY_SSL:
        server = smtplib.SMTP_SSL(smtp.host, smtp.port, timeout=timeout, context=context)
    else:
        server = smtplib.SMTP(smtp.host, smtp.port, timeout=timeout)
        if smtp.security == SECURITY_STARTTLS:
            server.starttls(context=context)
    server.login(smtp.user, password)
    return server


def test_connection(smtp: SmtpSettings, password: str):
    smtp.validate()
    server = connect(smtp, password)
    server.quit()


def send(smtp: SmtpSettings, password: str, message: EmailMessage):
    smtp.validate()
    if not password:
        raise ValueError('No hay contraseña guardada para el correo. Captúrela en Configuración > Correo')
    server = connect(smtp, password)
    try:
        server.send_message(message)
    finally:
        try:
            server.quit()
        except Exception:
            pass


# ---- historial ------------------------------------------------------------------
def log_send(session: Session, mail: InvoiceMail, recipients, subject, error: str | None = None) -> EnvioCorreo:
    row = EnvioCorreo(
        cliente_id=mail.cliente_id, contacto_rfc=mail.contacto_rfc, contacto_nombre=mail.contacto_nombre,
        uuid=mail.uuid, xml_path=str(mail.xml_path), pdf_path=str(mail.pdf_path),
        destinatarios=', '.join(recipients), asunto=subject, fecha=datetime.now(),
        estado='error' if error else 'enviado', error=(error or None) and error[:2000],
    )
    session.add(row)
    session.commit()
    return row


def history(session: Session, limit=300) -> list[EnvioCorreo]:
    return list(session.scalars(select(EnvioCorreo).order_by(EnvioCorreo.fecha.desc()).limit(limit)))


def send_invoice(session: Session, smtp: SmtpSettings, password: str, mail: InvoiceMail, recipients: list[str],
                 subject: str, body: str) -> EnvioCorreo:
    """Envía y registra en el historial (también los errores). Relanza el error para mostrarlo."""
    recipients = [contact_store.normalize_email(r) for r in recipients]
    invalid = [r for r in recipients if not contact_store.is_valid_email(r)]
    if not recipients:
        raise ValueError('Agregue al menos un destinatario')
    if invalid:
        raise ValueError('Correos no válidos: ' + ', '.join(invalid))
    for path in (mail.xml_path, mail.pdf_path):
        if not Path(path).is_file():
            raise ValueError(f'Ya no existe el archivo {path}')
    try:
        send(smtp, password, build_message(smtp, recipients, subject, body, [mail.pdf_path, mail.xml_path]))
    except Exception as error:
        log_send(session, mail, recipients, subject, error=str(error))
        raise
    return log_send(session, mail, recipients, subject)
