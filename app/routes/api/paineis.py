from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from peewee import DatabaseError

from app.database import DB_PATH, Favorito, normalizar_ticker
from app.migrations.runner import banco_sqlite, consultar_status, EstadoMigracaoInvalido
from app.services.security import exigir_usuario_api, exigir_csrf
from app.services.catalogo import obter_catalogo_acoes, ErroCatalogoAtivos
from app.services.painel_dados import buscar_macro, buscar_setores
from app.services.carteira import buscar_carteira_home

router = APIRouter()


@router.get('/api/paineis/macro')
def macro(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return buscar_macro()


@router.get('/api/paineis/setores')
def setores(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return buscar_setores()


@router.get('/api/conta/favoritos')
def favoritos(response: Response, usuario=Depends(exigir_usuario_api)):
    response.headers['Cache-Control'] = 'no-store'
    return buscar_carteira_home(usuario.id)


def escrever_favorito(usuario_id, ticker, adicionar):
    try:
        ticker = normalizar_ticker(ticker)
    except ValueError as erro:
        raise HTTPException(400, str(erro)) from erro
    if adicionar:
        try:
            acoes = obter_catalogo_acoes()
            if not any(a['ticker'] == ticker for a in acoes):
                # Não podemos confirmar ausência com um snapshot possivelmente antigo.
                raise HTTPException(503, 'Ativo não confirmado no catálogo disponível')
        except ErroCatalogoAtivos as erro:
            raise HTTPException(503, 'Catálogo indisponível') from erro
    try:
        caminho = Path(DB_PATH)
        if any(not m.aplicada for m in consultar_status(caminho)):
            raise HTTPException(503, 'Favoritos indisponíveis: migração pendente')
        banco = banco_sqlite(caminho, somente_leitura=False)
        with banco.connection_context(), banco.atomic():
            if adicionar:
                (Favorito.insert(usuario=usuario_id, ticker=ticker)
                 .on_conflict_ignore().bind(banco).execute())
            else:
                (Favorito.delete().where((Favorito.usuario == usuario_id) &
                    (Favorito.ticker == ticker)).bind(banco).execute())
    except (DatabaseError, FileNotFoundError, EstadoMigracaoInvalido, RuntimeError) as erro:
        raise HTTPException(503, 'Favoritos temporariamente indisponíveis') from erro
    return {'ticker': ticker, 'adicionado': adicionar}


@router.post('/api/conta/favoritos/{ticker}')
def adicionar(ticker: str, response: Response, usuario=Depends(exigir_usuario_api), _csrf=Depends(exigir_csrf)):
    response.headers['Cache-Control'] = 'no-store'
    return escrever_favorito(usuario.id, ticker, True)


@router.delete('/api/conta/favoritos/{ticker}')
def remover(ticker: str, response: Response, usuario=Depends(exigir_usuario_api), _csrf=Depends(exigir_csrf)):
    response.headers['Cache-Control'] = 'no-store'
    return escrever_favorito(usuario.id, ticker, False)
