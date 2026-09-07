from fastapi import APIRouter
from app.services.informacoes import buscar_ativo
from app.services.utils.formatar import formatar_ticker


router = APIRouter()

@router.get('/api/{ticker}')
def ativo(ticker: str):
    ticker_formatado = formatar_ticker(ticker)

    dados = buscar_ativo(ticker_formatado)

    return dados