import json
import math
import threading
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BRAPI_LIST_URL = 'https://brapi.dev/api/quote/list'
BRAPI_TIMEOUT = 4
CATALOGO_TTL_SEGUNDOS = 15 * 60
CATALOGO_RETRY_SEGUNDOS = 30

_cache_lock = threading.Lock()
_cache_acoes = None
_cache_expira_em = 0.0


class ErroCatalogoAtivos(Exception):
    """Indica que o catálogo de ações não está disponível no momento."""


def _numero_finito(valor):
    if isinstance(valor, bool) or valor is None:
        return None

    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None

    return numero if math.isfinite(numero) else None


def _normalizar_acao(item):
    if not isinstance(item, dict):
        return None

    if item.get('type') != 'stock' or item.get('subType') != 'stock':
        return None

    ticker_bruto = item.get('stock')
    if not isinstance(ticker_bruto, str):
        return None

    ticker = ticker_bruto.strip().upper()
    if not ticker or ticker.endswith('F'):
        return None

    nome_bruto = item.get('name')
    if not isinstance(nome_bruto, str) or not nome_bruto.strip():
        return None

    volume = _numero_finito(item.get('volume'))
    if volume is not None and volume.is_integer():
        volume = int(volume)

    return {
        'ticker': ticker,
        'nome': nome_bruto.strip(),
        'preco': _numero_finito(item.get('close')),
        'variacao': _numero_finito(item.get('change')),
        'volume': volume,
    }


def _buscar_lista_brapi():
    parametros = urlencode({
        'type': 'stock',
        'subType': 'stock',
        'limit': 1000,
    })
    requisicao = Request(
        f'{BRAPI_LIST_URL}?{parametros}',
        headers={
            'Accept': 'application/json',
            'User-Agent': 'Money-App/1.0',
        },
    )

    with urlopen(requisicao, timeout=BRAPI_TIMEOUT) as resposta:
        conteudo = resposta.read()

    dados = json.loads(conteudo)
    if not isinstance(dados, dict) or not isinstance(dados.get('stocks'), list):
        raise ValueError('Resposta inválida da Brapi')

    return dados['stocks']


def _carregar_catalogo():
    acoes = []
    tickers_vistos = set()

    for item in _buscar_lista_brapi():
        acao = _normalizar_acao(item)
        if acao is None or acao['ticker'] in tickers_vistos:
            continue

        tickers_vistos.add(acao['ticker'])
        acoes.append(acao)

    if not acoes:
        raise ValueError('A Brapi não retornou ações válidas')

    return tuple(acoes)


def obter_catalogo_acoes():
    """Retorna o catálogo da B3, evitando novas chamadas durante o TTL."""
    global _cache_acoes, _cache_expira_em

    agora = time.monotonic()
    if agora < _cache_expira_em:
        if _cache_acoes is not None:
            return _cache_acoes
        raise ErroCatalogoAtivos('O catálogo de ações está temporariamente indisponível')

    with _cache_lock:
        agora = time.monotonic()
        if agora < _cache_expira_em:
            if _cache_acoes is not None:
                return _cache_acoes
            raise ErroCatalogoAtivos(
                'O catálogo de ações está temporariamente indisponível'
            )

        try:
            novo_catalogo = _carregar_catalogo()
        except (
            HTTPError,
            URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
            UnicodeError,
            ValueError,
        ) as erro:
            _cache_expira_em = agora + CATALOGO_RETRY_SEGUNDOS
            if _cache_acoes is not None:
                return _cache_acoes
            raise ErroCatalogoAtivos(
                'Não foi possível carregar o catálogo de ações'
            ) from erro

        _cache_acoes = novo_catalogo
        _cache_expira_em = agora + CATALOGO_TTL_SEGUNDOS
        return _cache_acoes


def _texto_pesquisavel(valor):
    texto = unicodedata.normalize('NFKD', valor)
    sem_acentos = ''.join(
        caractere for caractere in texto
        if not unicodedata.combining(caractere)
    )
    return ' '.join(sem_acentos.casefold().split())


def buscar_sugestoes(consulta, limite=8):
    """Pesquisa ticker ou nome, priorizando as correspondências mais fortes."""
    termo = _texto_pesquisavel(consulta.strip())
    if not termo:
        return []

    correspondencias = []
    for acao in obter_catalogo_acoes():
        ticker = _texto_pesquisavel(acao['ticker'])
        nome = _texto_pesquisavel(acao['nome'])

        if ticker == termo:
            prioridade = 0
        elif ticker.startswith(termo):
            prioridade = 1
        elif nome.startswith(termo):
            prioridade = 2
        elif termo in nome:
            prioridade = 3
        else:
            continue

        correspondencias.append((prioridade, ticker, nome, acao))

    correspondencias.sort(key=lambda item: item[:3])
    return [
        {'ticker': acao['ticker'], 'nome': acao['nome']}
        for _, _, _, acao in correspondencias[:limite]
    ]
