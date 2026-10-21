from app.services.catalogo import ErroCatalogoAtivos, obter_catalogo_acoes


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


def buscar_rankings_mercado():
    """Calcula os três rankings usando o catálogo compartilhado da Brapi."""
    resultado = _resultado_vazio()

    try:
        acoes = obter_catalogo_acoes()

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
    except ErroCatalogoAtivos:
        return resultado

    return resultado
