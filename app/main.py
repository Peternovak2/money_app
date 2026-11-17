from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.database import criar_tabelas
from app.services.security import configuracao_cookie_sessao, obter_token_csrf

app = FastAPI(title='Money App')
app.state.asset_version = 'dev'

# Sessão autenticada via cookie assinado (itsdangerous)
SESSION_CONFIG = configuracao_cookie_sessao()
app.add_middleware(SessionMiddleware, **SESSION_CONFIG)

@app.on_event("startup")
def startup_event():
    # Cria as tabelas do banco na inicialização, se ainda não existirem
    criar_tabelas()


@app.middleware('http')
async def no_cache_middleware(request, call_next):
    response = await call_next(request)

    auth_paths = ['/login', '/cadastro', '/logout', '/conta']
    is_auth = any(request.url.path.startswith(p) for p in auth_paths)

    if request.url.path.startswith('/static') or request.url.path == '/' or request.url.path.startswith('/ativo') or is_auth:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

    return response

# Rotas
from app.routes.api.api import router as api_router
app.include_router(api_router)
from app.routes.api.paineis import router as paineis_router
app.include_router(paineis_router)

from app.routes.ativos import router as ativo_router
app.include_router(ativo_router)

from app.routes.auth import router as auth_router
app.include_router(auth_router)

from app.routes.conta import router as conta_router
app.include_router(conta_router)

from app.routes.mercado import router as mercado_router
app.include_router(mercado_router)

# Configura a rota para arquivos estáticos (CSS, JS, Imagens)
app.mount('/static', StaticFiles(directory='app/static'), name='static')

templates = Jinja2Templates(directory='app/templates')

# Filtros Jinja necessários para index.html
# (routes/ativos.py tem uma instância separada com os seus próprios filtros)
from app.services.utils.formatar import formatar_numero, formatar_variacao
templates.env.filters['formatar_numero'] = formatar_numero
templates.env.filters['formatar_variacao'] = formatar_variacao

from app.services.auth import obter_usuario_logado
from app.services.noticias import buscar_noticias_home
from app.services.populares import buscar_rankings_mercado

@app.get('/')
def home(request: Request):
    usuario = obter_usuario_logado(request)
    csrf_token = obter_token_csrf(request) if usuario else None
    rankings_mercado = buscar_rankings_mercado()
    noticias = buscar_noticias_home()
    return templates.TemplateResponse(
        request=request,
        name='index.html',
        context={
            'asset_version': app.state.asset_version,
            'usuario': usuario,
            'csrf_token': csrf_token,
            'rankings_mercado': rankings_mercado,
            'noticias': noticias,
        }
    )
