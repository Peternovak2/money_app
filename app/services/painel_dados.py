"""Séries diárias para uso local/educacional. Não são cotações em tempo real."""
import math
import threading
import time
from datetime import datetime, timezone

import yfinance as yf

from app.services.catalogo import obter_catalogo_acoes

INSTRUMENTOS = (
    ('BRL=X', 'USD/BRL', 'cambio', 'BRL por USD'),
    ('CL=F', 'Petróleo WTI', 'futuro', 'USD por barril'),
    ('GC=F', 'Ouro', 'futuro', 'USD por onça troy'),
    ('NG=F', 'Gás natural', 'futuro', 'USD por MMBtu'),
    ('HG=F', 'Cobre', 'futuro', 'USD por libra'),
)
# Rótulos traduzem exatamente as categorias do provedor, sem agregá-las.
SETORES = (('Finance', 'Financeiro'), ('Utilities', 'Utilidade pública'),
           ('Energy Minerals', 'Minerais energéticos'),
           ('Non-Energy Minerals', 'Minerais não energéticos'))
_cache = {}
_lock = threading.Lock()
TTL = 3600


def serie_diaria(simbolo, ajustado=False):
    dados = yf.Ticker(simbolo).history(period='1mo', interval='1d',
        auto_adjust=ajustado, actions=False, timeout=4, raise_errors=True)
    pontos = {}
    for indice, linha in dados.iterrows():
        valor = float(linha['Close'])
        if math.isfinite(valor) and valor > 0:
            pontos[indice.date().isoformat()] = valor
    return [{'data': data, 'valor': pontos[data]} for data in sorted(pontos)]


def resumir(serie):
    if len(serie) < 2:
        raise ValueError('Série insuficiente')
    return dict(estado='disponivel', valor=serie[-1]['valor'],
        variacao=100 * (serie[-1]['valor'] / serie[0]['valor'] - 1),
        inicio=serie[0]['data'], referencia=serie[-1]['data'], serie=serie)


def _em_cache(chave, carregar):
    with _lock:
        agora = time.monotonic()
        if chave in _cache and agora < _cache[chave][0]:
            return _cache[chave][1]
        resultado = carregar()
        for item in resultado:
            item['coletado_em'] = datetime.now(timezone.utc).isoformat()
        # Falhas também têm cache, evitando rajadas e retries por visitante.
        _cache[chave] = (time.monotonic() + TTL, resultado)
        return resultado


def buscar_macro():
    def carregar():
        resultado = []
        for simbolo, nome, tipo, unidade in INSTRUMENTOS:
            item = dict(id=simbolo, nome=nome, tipo=tipo, unidade=unidade,
                        fonte='Yahoo Finance', periodo='1mo', estado='indisponivel', serie=[])
            try:
                item.update(resumir(serie_diaria(simbolo)))
            except Exception:
                pass
            resultado.append(item)
        return resultado
    return _em_cache('macro', carregar)


def buscar_setores():
    def carregar():
        try:
            catalogo = obter_catalogo_acoes()
        except Exception:
            catalogo = ()
        resultado = []
        for categoria, nome in SETORES:
            item = dict(id=categoria, nome=nome, estado='indisponivel', serie=[],
                        fonte='Brapi (classificação) / Yahoo Finance (preços ajustados)',
                        tipo='amostra_money_app', unidade='base 100', periodo='1mo', membros=[])
            amostra = sorted((a for a in catalogo if a.get('setor') == categoria),
                key=lambda a: (-(a.get('volume') or 0), a['ticker']))[:2]
            series = []
            try:
                for acao in amostra:
                    serie = serie_diaria(acao['ticker'] + '.SA', ajustado=True)
                    if len(serie) < 15:
                        raise ValueError('Cobertura insuficiente')
                    series.append({p['data']: p['valor'] for p in serie})
                if len(series) != 2:
                    raise ValueError('Amostra insuficiente')
                datas = sorted(set(series[0]).intersection(series[1]))
                if len(datas) < 15:
                    raise ValueError('Datas incompatíveis')
                base = datas[0]
                historico = [dict(data=d, valor=50 * sum(s[d] / s[base] for s in series)) for d in datas]
                item.update(resumir(historico))
                item['membros'] = [a['ticker'] for a in amostra]
            except Exception:
                pass
            resultado.append(item)
        disponiveis = [i for i in resultado if i['estado'] == 'disponivel']
        # Só compara barras quando todas as amostras têm as mesmas datas extremas.
        if disponiveis:
            inicio = max(i['inicio'] for i in disponiveis)
            fim = min(i['referencia'] for i in disponiveis)
            for item in disponiveis:
                serie = [p for p in item['serie'] if inicio <= p['data'] <= fim]
                if len(serie) < 15 or serie[0]['data'] != inicio or serie[-1]['data'] != fim:
                    item.update(estado='indisponivel', serie=[])
                else:
                    base = serie[0]['valor']
                    serie = [dict(data=p['data'], valor=100*p['valor']/base) for p in serie]
                    item.update(resumir(serie))
        return resultado
    return _em_cache('setores', carregar)
