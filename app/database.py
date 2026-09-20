import os
from datetime import datetime

from peewee import (
    CharField,
    DateTimeField,
    ForeignKeyField,
    Model,
    SqliteDatabase,
)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'money.db')

db = SqliteDatabase(DB_PATH, pragmas={'foreign_keys': 1})

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


class Favorito(BaseModel):
    usuario = ForeignKeyField(Usuario, backref='favoritos', on_delete='CASCADE')
    ticker = CharField(max_length=20)
    criado_em = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'favoritos'
        indexes = (
            (('usuario', 'ticker'), True),
        )


def criar_tabelas():
    with db:
        db.create_tables([Usuario, Favorito], safe=True)
