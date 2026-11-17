from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.auth import obter_usuario_logado
from app.services.security import obter_token_csrf


router = APIRouter()
templates = Jinja2Templates(directory='app/templates')


@router.get('/conta', response_class=HTMLResponse)
def minha_conta(request: Request):
    usuario = obter_usuario_logado(request)

    if usuario is None:
        request.session.pop('user_id', None)
        return RedirectResponse(url='/login', status_code=303)

    usuario_publico = {
        'nome': usuario.nome,
        'email': usuario.email,
    }
    csrf_token = obter_token_csrf(request)

    response = templates.TemplateResponse(
        request=request,
        name='conta.html',
        context={
            'asset_version': request.app.state.asset_version,
            'usuario': usuario_publico,
            'csrf_token': csrf_token,
        },
    )
    response.headers['Cache-Control'] = (
        'no-store, no-cache, must-revalidate, max-age=0'
    )
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
