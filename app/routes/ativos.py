from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.auth import obter_usuario_logado
from app.services.favoritos import (
    adicionar_favorito,
    esta_favoritado,
    normalizar_ticker_favorito,
    remover_favorito,
)
from app.services.informacoes import buscar_ativo
from app.services.utils.formatar import formatar_ticker

router = APIRouter()

templates = Jinja2Templates(directory='app/templates')

@router.get('/ativo/{ticker}', response_class=HTMLResponse)
def ativo(request: Request, ticker: str):
    ticker_formatado = formatar_ticker(ticker)

    try:
        dados = buscar_ativo(ticker_formatado)
    except ValueError:
        return templates.TemplateResponse(
            request=request,
            name='erro.html',
            context={
                'ticker': ticker
            },
            status_code=404
        )

    usuario = obter_usuario_logado(request)
    try:
        ticker_canonico = normalizar_ticker_favorito(ticker_formatado)
    except ValueError:
        ticker_canonico = None

    favoritavel = ticker_canonico is not None
    favoritado = (
        esta_favoritado(usuario, ticker_canonico)
        if usuario and ticker_canonico
        else False
    )

    return templates.TemplateResponse(
        request=request,
        name='ativo.html',
        context={
            'dados': dados,
            'asset_version': 'dev',
            'usuario': usuario,
            'ticker_canonico': ticker_canonico,
            'favoritavel': favoritavel,
            'favoritado': favoritado,
        }
    )


@router.post('/ativo/{ticker}/favoritar')
def favoritar(request: Request, ticker: str):
    usuario = obter_usuario_logado(request)
    if usuario is None:
        return RedirectResponse(url='/login', status_code=303)

    try:
        ticker_canonico = normalizar_ticker_favorito(ticker)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro

    adicionar_favorito(usuario, ticker_canonico)
    return RedirectResponse(url=f'/ativo/{ticker_canonico}', status_code=303)


@router.post('/ativo/{ticker}/desfavoritar')
def desfavoritar(request: Request, ticker: str):
    usuario = obter_usuario_logado(request)
    if usuario is None:
        return RedirectResponse(url='/login', status_code=303)

    try:
        ticker_canonico = normalizar_ticker_favorito(ticker)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro

    remover_favorito(usuario, ticker_canonico)
    return RedirectResponse(url=f'/ativo/{ticker_canonico}', status_code=303)
