from datetime import datetime

from peewee import (
    CharField,
    DateTimeField,
    Model,
    SqliteDatabase,
)

db = SqliteDatabase('money.db')


class BaseModel(Model):
    class Meta:
        database = db


class Usuario(BaseModel):
    nome = CharField(max_length=100)
    email = CharField(max_length=255, unique=True)
    senha_hash = CharField(max_length=255)
    criado_em = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'usuarios'


def criar_tabelas():
    with db:
        db.create_tables([Usuario], safe=True)
