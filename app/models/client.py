from tortoise import fields
from tortoise.models import Model


class Client(Model):
    nombre = fields.TextField()
    apellido_paterno = fields.TextField()
    apellido_materno = fields.TextField()
    rfc = fields.TextField()

    def fullname(self):
        return f'{self.nombre} {self.apellido_paterno} {self.apellido_materno}'

    def __str__(self):
        return f'({self.rfc}) {self.fullname()}'
