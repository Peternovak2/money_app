from app.services.catalogo import ErroCatalogoAtivos, obter_catalogo_acoes


QUANTIDADE_POR_RANKING = 5
TAMANHO_PAGINA_PADRAO = 10
TAMANHOS_PAGINA = (10, 20, 50)
TIPOS_MOVIMENTO = {
    'altas': {
        'titulo': 'Maiores altas',
        'descricao': 'Ações com as maiores variações positivas no catálogo atual.',
    },
    'baixas': {
        'titulo': 'Maiores baixas',
        'descricao': 'Ações com as maiores variações negativas no catálogo atual.',
    },
}


class TipoRankingInvalido(ValueError):
    pass


class ParametrosPaginacaoInvalidos(ValueError):
    pass


class PaginaRankingInexistente(ValueError):
    pass


def _resultado_vazio():
    return {
        'fonte': 'brapi',
        'universo': 'acoes_b3_sem_mercado_fracionario',
        'criterio_mais_negociadas': 'volume_quantidade',
        'altas': [],
        'baixas': [],
        'mais_negociadas': [],
    }


def _ordenar_movimento(acoes, tipo):
    if tipo == 'altas':
        return sorted(
            (
                acao for acao in acoes
                if acao['variacao'] is not None and acao['variacao'] > 0
            ),
            key=lambda acao: acao['variacao'],
            reverse=True,
        )

    if tipo == 'baixas':
        return sorted(
            (
                acao for acao in acoes
                if acao['variacao'] is not None and acao['variacao'] < 0
            ),
            key=lambda acao: acao['variacao'],
        )

    raise TipoRankingInvalido('Tipo de ranking inválido')


def _validar_paginacao(pagina, tamanho_pagina):
    if isinstance(pagina, bool) or not isinstance(pagina, int) or pagina < 1:
        raise ParametrosPaginacaoInvalidos('Página inválida')

    if (
        isinstance(tamanho_pagina, bool)
        or not isinstance(tamanho_pagina, int)
        or tamanho_pagina not in TAMANHOS_PAGINA
    ):
        raise ParametrosPaginacaoInvalidos('Quantidade por página inválida')


def _montar_paginas_visiveis(pagina, total_paginas):
    if total_paginas <= 7:
        return list(range(1, total_paginas + 1))

    candidatas = {1, total_paginas}
    candidatas.update(
        range(
            max(1, pagina - 2),
            min(total_paginas, pagina + 2) + 1,
        )
    )

    paginas = []
    pagina_anterior = None
    for numero in sorted(candidatas):
        if pagina_anterior is not None and numero - pagina_anterior > 1:
            paginas.append(None)
        paginas.append(numero)
        pagina_anterior = numero

    return paginas


def _montar_paginacao(pagina, tamanho_pagina, total_itens):
    total_paginas = (
        (total_itens + tamanho_pagina - 1) // tamanho_pagina
        if total_itens
        else 0
    )

    if pagina > max(total_paginas, 1):
        raise PaginaRankingInexistente('Página do ranking não encontrada')

    inicio = (pagina - 1) * tamanho_pagina
    fim = min(inicio + tamanho_pagina, total_itens)

    return {
        'pagina': pagina,
        'tamanho_pagina': tamanho_pagina,
        'total_itens': total_itens,
        'total_paginas': total_paginas,
        'primeira_posicao': inicio + 1 if total_itens else 0,
        'ultima_posicao': fim,
        'tem_anterior': pagina > 1,
        'tem_proxima': pagina < total_paginas,
        'paginas': _montar_paginas_visiveis(pagina, total_paginas),
    }


def buscar_rankings_mercado():
    """Calcula os três rankings usando o catálogo compartilhado da Brapi."""
    resultado = _resultado_vazio()

    try:
        acoes = obter_catalogo_acoes()

        resultado['altas'] = _ordenar_movimento(
            acoes,
            'altas',
        )[:QUANTIDADE_POR_RANKING]
        resultado['baixas'] = _ordenar_movimento(
            acoes,
            'baixas',
        )[:QUANTIDADE_POR_RANKING]
        resultado['mais_negociadas'] = sorted(
            (acao for acao in acoes if acao['volume'] is not None and acao['volume'] > 0),
            key=lambda acao: acao['volume'],
            reverse=True,
        )[:QUANTIDADE_POR_RANKING]
    except ErroCatalogoAtivos:
        return resultado

    return resultado


def buscar_ranking_movimento(
    tipo,
    pagina=1,
    tamanho_pagina=TAMANHO_PAGINA_PADRAO,
):
    """Retorna uma página ordenada do ranking de altas ou baixas."""
    configuracao = TIPOS_MOVIMENTO.get(tipo)
    if configuracao is None:
        raise TipoRankingInvalido('Tipo de ranking inválido')

    _validar_paginacao(pagina, tamanho_pagina)

    resultado = {
        'tipo': tipo,
        'titulo': configuracao['titulo'],
        'descricao': configuracao['descricao'],
        'fonte': 'brapi',
        'itens': [],
        'indisponivel': False,
    }

    try:
        itens_ordenados = _ordenar_movimento(
            obter_catalogo_acoes(),
            tipo,
        )
    except ErroCatalogoAtivos:
        itens_ordenados = []
        resultado['indisponivel'] = True

    paginacao = _montar_paginacao(
        pagina,
        tamanho_pagina,
        len(itens_ordenados),
    )
    inicio = (pagina - 1) * tamanho_pagina
    fim = inicio + tamanho_pagina
    resultado['itens'] = itens_ordenados[inicio:fim]
    resultado['paginacao'] = paginacao

    return resultado
