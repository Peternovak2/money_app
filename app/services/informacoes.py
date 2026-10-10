import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
import yfinance as yf


ESTADOS_MERCADO_FECHADO = {'CLOSED', 'POST', 'POSTPOST', 'PRE', 'PREPRE'}
TIMEZONE_IBOVESPA = 'America/Sao_Paulo'


PERIODOS_HISTORICO = {
    '1mo': '1d',
    '3mo': '1d',
    '6mo': '1d',
    '1y': '1d',
    '5y': '1wk',
    'max': '1mo',
}


class PeriodoHistoricoInvalido(ValueError):
    pass


class AtivoHistoricoNaoEncontrado(ValueError):
    pass


class ErroConsultaHistorico(RuntimeError):
    pass


def _converter_float(valor):
    if pd.isna(valor):
        return None

    try:
        valor_convertido = float(valor)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(valor_convertido):
        return None

    return valor_convertido


def _normalizar_status_mercado(status_raw):
    if status_raw == 'REGULAR':
        return 'aberto'

    if (
        isinstance(status_raw, str)
        and status_raw in ESTADOS_MERCADO_FECHADO
    ):
        return 'fechado'

    return 'indisponivel'


def _obter_timezone_mercado(nome_timezone, fallback=None):
    for candidato in (nome_timezone, fallback):
        if not candidato or not isinstance(candidato, str):
            continue

        try:
            return ZoneInfo(candidato)
        except (ZoneInfoNotFoundError, ValueError):
            continue

    return None


def _converter_timestamp_mercado(timestamp, timezone_mercado):
    if timezone_mercado is None or isinstance(timestamp, bool):
        return None

    try:
        timestamp_convertido = float(timestamp)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(timestamp_convertido):
        return None

    try:
        data_utc = datetime.fromtimestamp(timestamp_convertido, tz=timezone.utc)
        return data_utc.astimezone(timezone_mercado)
    except (OverflowError, OSError, ValueError):
        return None


def buscar_historico_ativo(ticker, periodo='6mo'):
    if periodo not in PERIODOS_HISTORICO:
        raise PeriodoHistoricoInvalido('Período histórico inválido')

    intervalo = PERIODOS_HISTORICO[periodo]
    ativo = yf.Ticker(ticker)

    try:
        historico = ativo.history(
            period=periodo,
            interval=intervalo,
            actions=False,
            auto_adjust=False,
        )
    except Exception as erro:
        raise ErroConsultaHistorico('Não foi possível consultar o histórico') from erro

    if historico is None or historico.empty:
        try:
            info = ativo.info
        except Exception as erro:
            raise ErroConsultaHistorico('Não foi possível validar o ativo') from erro

        if not info or info.get('quoteType') is None:
            raise AtivoHistoricoNaoEncontrado('Ativo não encontrado')

        return {
            'ticker': ticker.removesuffix('.SA'),
            'periodo': periodo,
            'intervalo': intervalo,
            'pontos': [],
        }

    colunas_ohlc = ('Open', 'High', 'Low', 'Close')
    if any(coluna not in historico.columns for coluna in colunas_ohlc):
        raise ErroConsultaHistorico('O histórico não contém dados OHLC')

    pontos = []

    for indice, linha in historico.iterrows():
        if pd.isna(indice):
            continue

        abertura = _converter_float(linha.get('Open'))
        maxima = _converter_float(linha.get('High'))
        minima = _converter_float(linha.get('Low'))
        fechamento = _converter_float(linha.get('Close'))

        if None in (abertura, maxima, minima, fechamento):
            continue

        volume = _converter_float(linha.get('Volume'))

        pontos.append({
            'time': indice.date().isoformat(),
            'open': abertura,
            'high': maxima,
            'low': minima,
            'close': fechamento,
            'volume': int(volume) if volume is not None else None,
        })

    return {
        'ticker': ticker.removesuffix('.SA'),
        'periodo': periodo,
        'intervalo': intervalo,
        'pontos': pontos,
    }


def buscar_ativo(ticker):
    ativo = yf.Ticker(ticker)
    info = ativo.info

    if not info or info.get('quoteType') is None:
        raise ValueError('Ativo não encontrado')
    
    roe_raw = _converter_float(info.get("returnOnEquity"))
    margem_liquida_raw = _converter_float(info.get("profitMargins"))
    ev_ebitda_raw = _converter_float(info.get("enterpriseToEbitda"))
    divida_total_raw = _converter_float(info.get("totalDebt"))
    ebitda_raw = _converter_float(info.get("ebitda"))
    liquidez_corrente_raw = _converter_float(info.get("currentRatio"))
    caixa_total_raw = _converter_float(info.get("totalCash"))
    moeda_financeira = info.get("financialCurrency") or info.get("currency")

    if divida_total_raw is not None and ebitda_raw is not None and ebitda_raw != 0:
        divida_total_ebitda = divida_total_raw / ebitda_raw
    else:
        divida_total_ebitda = None

    return {
        "ticker": ticker,
        "nome": info.get("longName"),
        "preco": info.get("currentPrice"),
        "variacao_dia": info.get("regularMarketChangePercent"),
        "abertura": info.get("open"),
        "maxima": info.get("dayHigh"),
        "minima": info.get("dayLow"),
        "volume": info.get("volume"),
        "market_cap": info.get("marketCap"),
        "setor": info.get("sector"),
        "industria": info.get("industry"),
        "dividend_yield": info.get("dividendYield"),
        "pe": info.get("trailingPE"),
        "eps": info.get("trailingEps"),
        "moeda": info.get("currency"),
        "pvp": info.get("priceToBook"),
        "roe": roe_raw * 100 if roe_raw is not None else None,
        "margem_liquida": margem_liquida_raw * 100 if margem_liquida_raw is not None else None,
        "ev_ebitda": ev_ebitda_raw,
        "divida_total": divida_total_raw,
        "divida_total_ebitda": divida_total_ebitda,
        "liquidez_corrente": liquidez_corrente_raw,
        "caixa_total": caixa_total_raw,
        "moeda_financeira": moeda_financeira,
    }


def _buscar_item_mercado(ticker, incluir_status=False, timezone_fallback=None):
    """Busca cotação de um único ticker para o resumo de mercado.

    Retorna um dict com os campos normalizados ou None em caso de qualquer
    falha — garantindo que um erro externo não quebre a home.

    Nota: regularMarketChangePercent já vem em percentual (ex.: -0.268
    representa -0,268%), portanto NÃO é multiplicado por 100.
    """
    try:
        info = yf.Ticker(ticker).info

        if not info or info.get('regularMarketPrice') is None:
            return None

        nome = info.get('longName') or info.get('shortName')
        valor = _converter_float(info.get('regularMarketPrice'))
        # regularMarketChangePercent já está em percentual — não multiplicar
        variacao = _converter_float(info.get('regularMarketChangePercent'))
        moeda = info.get('currency')
        timestamp = info.get('regularMarketTime')

        item = {
            'nome': nome,
            'valor': valor,
            'variacao': variacao,
            'moeda': moeda,
            'timestamp': timestamp,
        }

        if incluir_status:
            status_raw = info.get('marketState')
            timezone_mercado = _obter_timezone_mercado(
                info.get('exchangeTimezoneName'),
                fallback=timezone_fallback,
            )

            item.update({
                'status_raw': status_raw,
                'status': _normalizar_status_mercado(status_raw),
                'ultima_atualizacao': _converter_timestamp_mercado(
                    timestamp,
                    timezone_mercado,
                ),
                'timezone': (
                    timezone_mercado.key
                    if timezone_mercado is not None
                    else None
                ),
            })

        return item
    except Exception:
        return None


def buscar_resumo_mercado():
    """Retorna cotações de Ibovespa e Dólar para o resumo de mercado da home.

    Cada ticker falha de forma independente: se um falhar, o outro ainda é
    retornado. A home nunca deve gerar HTTP 500 por causa desta função.

    Retorno:
        {
            'ibovespa': dict | None,
            'dolar':    dict | None,
        }
    """
    return {
        'ibovespa': _buscar_item_mercado(
            '^BVSP',
            incluir_status=True,
            timezone_fallback=TIMEZONE_IBOVESPA,
        ),
        'dolar': _buscar_item_mercado('USDBRL=X'),
    }
