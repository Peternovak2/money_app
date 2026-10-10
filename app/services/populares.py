import json
import math
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BRAPI_LIST_URL = 'https://brapi.dev/api/quote/list'
BRAPI_TIMEOUT = 4
QUANTIDADE_POR_RANKING = 5


def _resultado_vazio():
    return {
        'fonte': 'brapi',
        'universo': 'acoes_b3_sem_mercado_fracionario',
        'criterio_mais_negociadas': 'volume_quantidade',
        'altas': [],
        'baixas': [],
        'mais_negociadas': [],
    }


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

    nome = nome_bruto.strip()
    volume = _numero_finito(item.get('volume'))

    if volume is not None and volume.is_integer():
        volume = int(volume)

    return {
        'ticker': ticker,
        'nome': nome,
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


def buscar_rankings_mercado():
    """Busca uma lista ampla na Brapi e calcula os três rankings localmente."""
    resultado = _resultado_vazio()

    try:
        itens = _buscar_lista_brapi()
        acoes = []

        for item in itens:
            acao = _normalizar_acao(item)
            if acao is not None:
                acoes.append(acao)

        resultado['altas'] = sorted(
            (acao for acao in acoes if acao['variacao'] is not None and acao['variacao'] > 0),
            key=lambda acao: acao['variacao'],
            reverse=True,
        )[:QUANTIDADE_POR_RANKING]
        resultado['baixas'] = sorted(
            (acao for acao in acoes if acao['variacao'] is not None and acao['variacao'] < 0),
            key=lambda acao: acao['variacao'],
        )[:QUANTIDADE_POR_RANKING]
        resultado['mais_negociadas'] = sorted(
            (acao for acao in acoes if acao['volume'] is not None and acao['volume'] > 0),
            key=lambda acao: acao['volume'],
            reverse=True,
        )[:QUANTIDADE_POR_RANKING]
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
        return resultado

    return resultado
