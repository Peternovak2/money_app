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
