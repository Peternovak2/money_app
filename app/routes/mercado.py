from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.auth import obter_usuario_logado
from app.services.populares import (
    PaginaRankingInexistente,
    ParametrosPaginacaoInvalidos,
    TipoRankingInvalido,
    buscar_ranking_movimento,
)
from app.services.security import obter_token_csrf
from app.services.utils.formatar import formatar_numero, formatar_variacao


router = APIRouter()

templates = Jinja2Templates(directory='app/templates')
templates.env.filters['formatar_numero'] = formatar_numero
templates.env.filters['formatar_variacao'] = formatar_variacao


@router.get('/mercado/{tipo}', response_class=HTMLResponse)
def ranking_mercado(
    request: Request,
    tipo: str,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query()] = 10,
):
    try:
        ranking = buscar_ranking_movimento(
            tipo,
            pagina=page,
            tamanho_pagina=page_size,
        )
    except TipoRankingInvalido as erro:
        raise HTTPException(status_code=404, detail='Ranking não encontrado') from erro
    except ParametrosPaginacaoInvalidos as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    except PaginaRankingInexistente as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro

    usuario = obter_usuario_logado(request)
    csrf_token = obter_token_csrf(request) if usuario else None

    return templates.TemplateResponse(
        request=request,
        name='ranking.html',
        context={
            'asset_version': request.app.state.asset_version,
            'ranking': ranking,
            'usuario': usuario,
            'csrf_token': csrf_token,
        },
    )
