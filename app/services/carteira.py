from pathlib import Path

from peewee import DatabaseError

from app.database import DB_PATH, Favorito
from app.migrations.runner import (
    EstadoMigracaoInvalido,
    banco_sqlite,
    consultar_status,
)
from app.services.catalogo import ErroCatalogoAtivos, obter_catalogo_acoes


def buscar_carteira_home(usuario_id, *, caminho_banco=None):
    """Lista de acompanhamento, sem posições financeiras nem escritas no banco.

    O chamador deve obter a identidade da sessão autenticada. O caminho opcional
    permite testar em SQLite temporário; não é exposto por parâmetros HTTP.
    """
    if usuario_id is None:
        return {'estado': 'anonimo', 'ativos': []}
    if isinstance(usuario_id, bool) or not isinstance(usuario_id, int) or usuario_id < 1:
        return {'estado': 'indisponivel', 'ativos': []}

    caminho = Path(caminho_banco if caminho_banco is not None else DB_PATH)
    try:
        if any(not migracao.aplicada for migracao in consultar_status(caminho)):
            return {'estado': 'indisponivel', 'ativos': []}
        leitura = banco_sqlite(caminho, somente_leitura=True)
        with leitura.connection_context():
            # bind() associa somente esta consulta, sem alterar os modelos globais.
            consulta = (Favorito.select(Favorito.ticker)
                        .where(Favorito.usuario == usuario_id)
                        .order_by(Favorito.criado_em.desc(), Favorito.id.desc())
                        .limit(4).bind(leitura).tuples())
            tickers = [ticker for (ticker,) in consulta]
    except (DatabaseError, EstadoMigracaoInvalido, FileNotFoundError, RuntimeError):
        return {'estado': 'indisponivel', 'ativos': []}

    if not tickers:
        return {'estado': 'vazio', 'ativos': []}
    try:
        # Mesmo catálogo em cache usado pelos rankings; não consulta cada ativo.
        catalogo = {acao['ticker']: acao for acao in obter_catalogo_acoes()}
    except ErroCatalogoAtivos:
        catalogo = {}
    ativos = []
    for ticker in tickers:
        acao = catalogo.get(ticker, {})
        ativos.append({
            'ticker': ticker,
            'nome': acao.get('nome') or ticker,
            'logo': acao.get('logo'),
            'setor': acao.get('setor') or 'Sem classificação',
            'preco': acao.get('preco'),
            'variacao': acao.get('variacao'),
        })
    return {'estado': 'sucesso', 'ativos': ativos}
