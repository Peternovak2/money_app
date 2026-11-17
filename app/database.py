import os
import re
from datetime import datetime

from peewee import (
    CharField,
    Check,
    DateTimeField,
    ForeignKeyField,
    Model,
    SqliteDatabase,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'money.db')

db = SqliteDatabase(DB_PATH, pragmas={'foreign_keys': 1})

PADRAO_TICKER = re.compile(r'^[A-Z0-9]{1,20}$')


def normalizar_ticker(valor: str) -> str:
    if not isinstance(valor, str) or not valor.isprintable():
        raise ValueError('Ticker inválido.')

    ticker = valor.strip().upper()
    if not PADRAO_TICKER.fullmatch(ticker):
        raise ValueError('Ticker inválido.')
    return ticker


class TickerField(CharField):
    def db_value(self, valor):
        return super().db_value(normalizar_ticker(valor))


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
    usuario = ForeignKeyField(
        Usuario,
        backref='favoritos',
        column_name='usuario_id',
        on_delete='CASCADE',
        index=False,
    )
    ticker = TickerField(
        max_length=20,
        constraints=[
            Check(
                "length(ticker) BETWEEN 1 AND 20 "
                "AND ticker NOT GLOB '*[^A-Z0-9]*'"
            )
        ],
    )
    criado_em = DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        self.ticker = normalizar_ticker(self.ticker)
        return super().save(*args, **kwargs)

    class Meta:
        table_name = 'favoritos'
        indexes = (
            (('usuario', 'ticker'), True),
        )


def criar_tabelas():
    with db:
        db.create_tables([Usuario], safe=True)
