from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI(title='Money App')
app.state.asset_version = 'dev'


@app.middleware('http')
async def no_cache_middleware(request, call_next):
    response = await call_next(request)

    if request.url.path.startswith('/static') or request.url.path == '/' or request.url.path.startswith('/ativo'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

    return response

# Rotas
from app.routes.api.api import router as api_router
app.include_router(api_router)

from app.routes.ativos import router as ativo_router
app.include_router(ativo_router)

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
