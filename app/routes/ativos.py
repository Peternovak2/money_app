from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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

    return templates.TemplateResponse(
        request=request,
        name='ativo.html',
        context={
            'dados': dados,
            'asset_version': 'dev'
        }
    )