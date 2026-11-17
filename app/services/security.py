import os
import secrets
from collections.abc import Mapping
from hmac import compare_digest

from fastapi import Header, HTTPException, Request

from app.database import Usuario
from app.services.auth import obter_usuario_logado


CSRF_SESSION_KEY = 'csrf_token'
CSRF_HEADER_NAME = 'X-CSRF-Token'


def _valor_booleano(valor: str | None, *, padrao: bool = False) -> bool:
    if valor is None:
        return padrao

    normalizado = valor.strip().lower()
    if normalizado in {'1', 'true', 'yes', 'on'}:
        return True
    if normalizado in {'0', 'false', 'no', 'off'}:
        return False
    raise ValueError('Configuração booleana de sessão inválida.')


def configuracao_cookie_sessao(
    ambiente: Mapping[str, str] | None = None,
) -> dict:
    variaveis = os.environ if ambiente is None else ambiente
    secret_key = variaveis.get('SECRET_KEY')
    if not secret_key:
        raise ValueError('A variável de ambiente SECRET_KEY deve estar definida.')

    app_env = variaveis.get('APP_ENV', 'development').strip().lower()
    https_explicito = _valor_booleano(
        variaveis.get('SESSION_HTTPS_ONLY'),
        padrao=False,
    )

    return {
        'secret_key': secret_key,
        'same_site': 'lax',
        'https_only': app_env == 'production' or https_explicito,
    }


def renovar_token_csrf(request: Request) -> str:
    token = secrets.token_urlsafe(32)
    request.session[CSRF_SESSION_KEY] = token
    return token


def obter_token_csrf(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)
    if isinstance(token, str) and token:
        return token
    return renovar_token_csrf(request)


def validar_token_csrf(request: Request, token_recebido: str | None) -> None:
    token_esperado = request.session.get(CSRF_SESSION_KEY)
    if (
        not isinstance(token_esperado, str)
        or not isinstance(token_recebido, str)
        or not compare_digest(token_esperado, token_recebido)
    ):
        raise HTTPException(status_code=403, detail='Token CSRF inválido')


def exigir_csrf(
    request: Request,
    x_csrf_token: str | None = Header(default=None, alias=CSRF_HEADER_NAME),
) -> None:
    validar_token_csrf(request, x_csrf_token)


def exigir_usuario_api(request: Request) -> Usuario:
    usuario = obter_usuario_logado(request)
    if usuario is None:
        request.session.pop('user_id', None)
        raise HTTPException(status_code=401, detail='Autenticação necessária')
    return usuario
