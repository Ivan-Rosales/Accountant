"""Contactos por cliente (clientes de mi cliente) y sus correos."""
import re
from dataclasses import dataclass, field

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from models import Cliente, Contacto, ContactoEmail

EMAIL_PATTERN = re.compile(r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$')


def normalize_email(email: str) -> str:
    return (email or '').strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(normalize_email(email)))


def split_emails(text: str) -> list[str]:
    """'a@x.com; b@y.com, c@z.com' -> ['a@x.com', 'b@y.com', 'c@z.com'] (sin duplicados)."""
    result = []
    for part in re.split(r'[;,\s]+', text or ''):
        email = normalize_email(part)
        if email and email not in result:
            result.append(email)
    return result


@dataclass
class ContactView:
    id: int
    rfc: str
    nombre: str
    emails: list = field(default_factory=list)

    def __str__(self):
        return f'({self.rfc}) {self.nombre}'.strip()


def list_contacts(session: Session, client: Cliente) -> list[ContactView]:
    contacts = session.scalars(select(Contacto).where(Contacto.cliente_id == client.id)
                               .order_by(Contacto.nombre, Contacto.rfc)).all()
    emails = {}
    if contacts:
        rows = session.scalars(select(ContactoEmail).where(
            ContactoEmail.contacto_id.in_([c.id for c in contacts])).order_by(ContactoEmail.email))
        for row in rows:
            emails.setdefault(row.contacto_id, []).append(row.email)
    return [ContactView(c.id, c.rfc, c.nombre or '', emails.get(c.id, [])) for c in contacts]


def find_contact(session: Session, client: Cliente, rfc: str) -> Contacto | None:
    return session.scalar(select(Contacto).where(Contacto.cliente_id == client.id,
                                                 Contacto.rfc == (rfc or '').strip().upper()))


def save_contact(session: Session, client: Cliente, rfc: str, nombre: str, contact_id: int | None = None) -> Contacto:
    rfc = (rfc or '').strip().upper()
    if not 12 <= len(rfc) <= 13:
        raise ValueError('El RFC debe tener 12 o 13 caracteres')
    existing = find_contact(session, client, rfc)
    if existing is not None and existing.id != contact_id:
        raise ValueError(f'Ya existe un contacto con RFC {rfc}')

    contact = session.get(Contacto, contact_id) if contact_id else Contacto(cliente_id=client.id)
    contact.rfc, contact.nombre = rfc, (nombre or '').strip()
    session.add(contact)
    session.commit()
    return contact


def delete_contacts(session: Session, contact_ids: list[int]):
    session.execute(delete(ContactoEmail).where(ContactoEmail.contacto_id.in_(contact_ids)))
    session.execute(delete(Contacto).where(Contacto.id.in_(contact_ids)))
    session.commit()


def add_emails(session: Session, contact_id: int, emails: list[str]) -> list[str]:
    """Agrega los correos válidos que no existan. Devuelve los inválidos."""
    existing = set(session.scalars(select(ContactoEmail.email).where(ContactoEmail.contacto_id == contact_id)))
    invalid = []
    for email in map(normalize_email, emails):
        if not is_valid_email(email):
            invalid.append(email)
        elif email not in existing:
            session.add(ContactoEmail(contacto_id=contact_id, email=email))
            existing.add(email)
    session.commit()
    return invalid


def remove_emails(session: Session, contact_id: int, emails: list[str]):
    session.execute(delete(ContactoEmail).where(ContactoEmail.contacto_id == contact_id,
                                                ContactoEmail.email.in_([normalize_email(e) for e in emails])))
    session.commit()


def upsert_contact_with_emails(session: Session, client: Cliente, rfc: str, nombre: str, emails: list[str]) -> list[str]:
    """Crea el contacto si no existe y le agrega los correos. Devuelve los inválidos."""
    contact = find_contact(session, client, rfc)
    if contact is None:
        contact = save_contact(session, client, rfc, nombre)
    return add_emails(session, contact.id, emails)
