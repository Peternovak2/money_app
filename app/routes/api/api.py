from fastapi import APIRouter, HTTPException
from app.services.informacoes import buscar_ativo
from app.services.utils.formatar import formatar_ticker

router = APIRouter()

@router.get('/api/{ticker}')
def ativo(ticker: str):
    ticker_formatado = formatar_ticker(ticker)

    try:
        dados = buscar_ativo(ticker_formatado)
    except ValueError:
        raise HTTPException(status_code=404, detail='Ativo não encontrado')

    return dados