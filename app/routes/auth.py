from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.auth import autenticar, criar_usuario

router = APIRouter()

templates = Jinja2Templates(directory='app/templates')


# ── Cadastro ──────────────────────────────────────────────────────────────────

@router.get('/cadastro', response_class=HTMLResponse)
def cadastro_get(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='cadastro.html',
        context={},
    )


@router.post('/cadastro', response_class=HTMLResponse)
def cadastro_post(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
):
    try:
        criar_usuario(nome=nome, email=email, senha=senha)
    except ValueError as e:
        return templates.TemplateResponse(
            request=request,
            name='cadastro.html',
            context={'erro': str(e)},
            status_code=400,
        )

    return RedirectResponse(url='/login', status_code=303)


# ── Login ─────────────────────────────────────────────────────────────────────

@router.get('/login', response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='login.html',
        context={},
    )


@router.post('/login', response_class=HTMLResponse)
def login_post(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
):
    usuario = autenticar(email=email, senha=senha)

    if usuario is None:
        return templates.TemplateResponse(
            request=request,
            name='login.html',
            context={'erro': 'E-mail ou senha inválidos.'},
            status_code=401,
        )

    request.session['user_id'] = usuario.id

    return RedirectResponse(url='/', status_code=303)


# ── Logout ────────────────────────────────────────────────────────────────────

@router.get('/logout')
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url='/', status_code=303)
