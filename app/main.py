from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import os

from app.database import criar_tabelas

app = FastAPI(title='Money App')
app.state.asset_version = 'dev'

# Sessão autenticada via cookie assinado (itsdangerous)
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("A variável de ambiente SECRET_KEY deve estar definida.")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

@app.on_event("startup")
def startup_event():
    # Cria as tabelas do banco na inicialização, se ainda não existirem
    criar_tabelas()


@app.middleware('http')
async def no_cache_middleware(request, call_next):
    response = await call_next(request)

    auth_paths = ['/login', '/cadastro', '/logout']
    is_auth = any(request.url.path.startswith(p) for p in auth_paths)

    if request.url.path.startswith('/static') or request.url.path == '/' or request.url.path.startswith('/ativo') or is_auth:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

    return response

# Rotas
from app.routes.api.api import router as api_router
app.include_router(api_router)

from app.routes.ativos import router as ativo_router
app.include_router(ativo_router)

from app.routes.auth import router as auth_router
app.include_router(auth_router)

# Configura a rota para arquivos estáticos (CSS, JS, Imagens)
app.mount('/static', StaticFiles(directory='app/static'), name='static')

templates = Jinja2Templates(directory='app/templates')

@app.get('/')
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='index.html',
        context={'asset_version': app.state.asset_version}
    )
