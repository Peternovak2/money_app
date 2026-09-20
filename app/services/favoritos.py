import re

from app.database import Favorito, Usuario


def normalizar_ticker_favorito(ticker: str) -> str:
    ticker_canonico = ticker.strip().upper()

    if ticker_canonico.endswith('.SA'):
        ticker_canonico = ticker_canonico[:-3]

    if not re.fullmatch(r'[A-Z]{4}\d{1,2}', ticker_canonico):
        raise ValueError('Ticker inválido.')

    return ticker_canonico


def adicionar_favorito(usuario: Usuario, ticker: str) -> Favorito:
    ticker_canonico = normalizar_ticker_favorito(ticker)
    favorito, _ = Favorito.get_or_create(
        usuario=usuario,
        ticker=ticker_canonico,
    )
    return favorito


def remover_favorito(usuario: Usuario, ticker: str) -> int:
    ticker_canonico = normalizar_ticker_favorito(ticker)
    return (
        Favorito.delete()
        .where(
            (Favorito.usuario == usuario)
            & (Favorito.ticker == ticker_canonico)
        )
        .execute()
    )


def esta_favoritado(usuario: Usuario, ticker: str) -> bool:
    ticker_canonico = normalizar_ticker_favorito(ticker)
    return (
        Favorito.select()
        .where(
            (Favorito.usuario == usuario)
            & (Favorito.ticker == ticker_canonico)
        )
        .exists()
    )
