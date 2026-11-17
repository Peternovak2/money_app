from typing import Literal
from fastapi import APIRouter, HTTPException, Query, Response
from app.services.catalogo import (
    ErroCatalogoAtivos,
    buscar_sugestoes,
    buscar_descoberta,
)
from app.services.informacoes import (
    AtivoHistoricoNaoEncontrado,
    ErroConsultaHistorico,
    PeriodoHistoricoInvalido,
    buscar_ativo,
    buscar_historico_ativo,
)
from app.services.utils.formatar import formatar_ticker, formatar_ticker_historico

from app.services.sessao_b3 import obter_sessao_b3

router = APIRouter()


@router.get('/api/ativos/sugestoes')
def sugestoes_ativos(
    q: str = Query(min_length=1, max_length=60),
    limite: int = Query(default=8, ge=1, le=10),
    categoria: Literal['todos', 'acao'] = 'todos',
):
    if any(not caractere.isprintable() for caractere in q):
        raise HTTPException(status_code=400, detail='Consulta inválida')

    consulta = q.strip()
    if not consulta:
        raise HTTPException(status_code=400, detail='Consulta inválida')

    try:
        if categoria == 'todos':
            return buscar_sugestoes(consulta, limite)
        return buscar_sugestoes(consulta, limite, categoria)
    except ErroCatalogoAtivos as erro:
        raise HTTPException(
            status_code=503,
            detail='A busca de ativos está indisponível no momento',
        ) from erro


@router.get('/api/ativos/descoberta')
def descoberta_ativos(
    limite: int = Query(default=8, ge=1, le=10),
    categoria: Literal['todos', 'acao'] = 'todos',
):
    try:
        return buscar_descoberta(limite, categoria)
    except ErroCatalogoAtivos as erro:
        raise HTTPException(status_code=503, detail='A descoberta de ativos está indisponível no momento') from erro

@router.get('/api/mercado/sessao')
def sessao_mercado(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return obter_sessao_b3()

@router.get('/api/{ticker}')
def ativo(ticker: str):
    ticker_formatado = formatar_ticker(ticker)

    try:
        dados = buscar_ativo(ticker_formatado)
    except ValueError:
        raise HTTPException(status_code=404, detail='Ativo não encontrado')

    return dados


@router.get('/api/{ticker}/historico')
def historico_ativo(ticker: str, periodo: str = '6mo'):
    try:
        ticker_formatado = formatar_ticker_historico(ticker)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro

    try:
        return buscar_historico_ativo(ticker_formatado, periodo)
    except PeriodoHistoricoInvalido as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    except AtivoHistoricoNaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except ErroConsultaHistorico as erro:
        raise HTTPException(
            status_code=502,
            detail='Não foi possível consultar o histórico no momento',
        ) from erro
