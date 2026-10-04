import math


def formatar_ticker(ticker: str):
    ticker = ticker.upper()

    if '.' in ticker or '-' in ticker:
        return ticker

    return f"{ticker}.SA"


VALOR_INDISPONIVEL = '—'


def formatar_numero(valor, casas_decimais=2):
    if valor is None:
        return VALOR_INDISPONIVEL

    try:
        valor_formatado = f'{valor:,.{casas_decimais}f}'
    except (TypeError, ValueError):
        return VALOR_INDISPONIVEL

    return valor_formatado.translate(str.maketrans({',': '.', '.': ','}))


def formatar_inteiro(valor):
    return formatar_numero(valor, casas_decimais=0)


def formatar_monetario(valor, moeda=None, casas_decimais=2):
    valor_formatado = formatar_numero(valor, casas_decimais)

    if valor_formatado == VALOR_INDISPONIVEL or not moeda:
        return valor_formatado

    return f'{valor_formatado} {moeda}'


def formatar_monetario_compacto(valor, moeda=None):
    try:
        valor_numerico = float(valor)
    except (TypeError, ValueError):
        return VALOR_INDISPONIVEL

    if not math.isfinite(valor_numerico):
        return VALOR_INDISPONIVEL

    escalas = (
        (1_000_000_000_000, 'tri'),
        (1_000_000_000, 'bi'),
        (1_000_000, 'mi'),
        (1_000, 'mil'),
    )
    divisor = 1
    sufixo = ''

    for limite, escala in escalas:
        if abs(valor_numerico) >= limite:
            divisor = limite
            sufixo = escala
            break

    valor_formatado = formatar_numero(valor_numerico / divisor, 1)
    partes = [valor_formatado]

    if sufixo:
        partes.append(sufixo)

    if moeda:
        partes.append(moeda)

    return ' '.join(partes)


def formatar_percentual(valor, casas_decimais=2):
    valor_formatado = formatar_numero(valor, casas_decimais)

    if valor_formatado == VALOR_INDISPONIVEL:
        return valor_formatado

    return f'{valor_formatado}%'
