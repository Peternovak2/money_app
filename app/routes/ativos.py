from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.auth import obter_usuario_logado
from app.services.informacoes import buscar_ativo
from app.services.utils.formatar import (
    formatar_inteiro,
    formatar_monetario,
    formatar_monetario_compacto,
    formatar_numero,
    formatar_percentual,
    formatar_ticker,
)

router = APIRouter()

templates = Jinja2Templates(directory='app/templates')
templates.env.filters['formatar_inteiro'] = formatar_inteiro
templates.env.filters['formatar_monetario'] = formatar_monetario
templates.env.filters['formatar_monetario_compacto'] = formatar_monetario_compacto
templates.env.filters['formatar_numero'] = formatar_numero
templates.env.filters['formatar_percentual'] = formatar_percentual

@router.get('/ativo/{ticker}', response_class=HTMLResponse)
def ativo(request: Request, ticker: str):
    ticker_formatado = formatar_ticker(ticker)
    ticker_exibicao = ticker_formatado.removesuffix('.SA')

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

    return templates.TemplateResponse(
        request=request,
        name='ativo.html',
        context={
            'dados': dados,
            'asset_version': 'dev',
            'usuario': obter_usuario_logado(request),
            'ticker_exibicao': ticker_exibicao,
        }
    )
