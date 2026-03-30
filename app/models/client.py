from tortoise import fields
from tortoise.models import Model


class Client(Model):
    name = fields.TextField()
    last_name = fields.TextField()
    rfc = fields.TextField()
