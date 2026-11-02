from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from peewee import Database, OperationalError, SqliteDatabase

from app.migrations.versions import MIGRACOES


SQL_TABELA_MIGRACOES = '''
CREATE TABLE "schema_migrations" (
    "versao" INTEGER NOT NULL PRIMARY KEY,
    "nome" VARCHAR(255) NOT NULL UNIQUE,
    "checksum" CHAR(64) NOT NULL,
    "aplicada_em" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)
'''


class EstadoMigracaoInvalido(RuntimeError):
    pass


@dataclass(frozen=True)
class StatusMigracao:
    versao: int
    nome: str
    aplicada: bool


@contextmanager
def _conexao(database: Database):
    abriu_conexao = database.is_closed()
    if abriu_conexao:
        database.connect()
    try:
        yield
    finally:
        if abriu_conexao and not database.is_closed():
            database.close()


def _habilitar_chaves_estrangeiras(database: Database) -> None:
    database.execute_sql('PRAGMA foreign_keys = ON')
    resultado = database.execute_sql('PRAGMA foreign_keys').fetchone()
    if resultado is None or resultado[0] != 1:
        raise RuntimeError('Não foi possível habilitar foreign_keys no SQLite.')


def _tabela_existe(database: Database, nome: str) -> bool:
    cursor = database.execute_sql(
        '''
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        ''',
        (nome,),
    )
    return cursor.fetchone() is not None


def _migracoes_aplicadas(database: Database) -> dict[int, tuple[str, str]]:
    if not _tabela_existe(database, 'schema_migrations'):
        return {}

    try:
        registros = database.execute_sql(
            '''
            SELECT versao, nome, checksum
            FROM schema_migrations
            ORDER BY versao
            '''
        ).fetchall()
    except OperationalError as erro:
        raise EstadoMigracaoInvalido(
            'A tabela schema_migrations possui estrutura incompatível.'
        ) from erro

    return {
        versao: (nome, checksum)
        for versao, nome, checksum in registros
    }


def _obter_status_conectado(database: Database) -> list[StatusMigracao]:
    aplicadas = _migracoes_aplicadas(database)
    conhecidas = {migracao.VERSAO: migracao for migracao in MIGRACOES}

    desconhecidas = sorted(set(aplicadas) - set(conhecidas))
    if desconhecidas:
        raise EstadoMigracaoInvalido(
            'Versões de migração desconhecidas no banco: '
            + ', '.join(str(versao) for versao in desconhecidas)
        )

    versoes_aplicadas = set(aplicadas)
    for versao in sorted(versoes_aplicadas):
        anteriores = {
            conhecida
            for conhecida in conhecidas
            if conhecida < versao
        }
        faltantes = sorted(anteriores - versoes_aplicadas)
        if faltantes:
            raise EstadoMigracaoInvalido(
                f'A migração {versao} foi aplicada antes das versões '
                + ', '.join(str(item) for item in faltantes)
            )

    status = []
    for migracao in MIGRACOES:
        registro = aplicadas.get(migracao.VERSAO)
        aplicada = registro is not None

        if registro is not None:
            nome, checksum = registro
            if nome != migracao.NOME:
                raise EstadoMigracaoInvalido(
                    f'Nome inconsistente para a migração {migracao.VERSAO}.'
                )
            if checksum != migracao.CHECKSUM:
                raise EstadoMigracaoInvalido(
                    f'Checksum inconsistente para a migração {migracao.VERSAO}.'
                )

        problemas = migracao.problemas_estado(database, aplicada=aplicada)
        if problemas:
            raise EstadoMigracaoInvalido(
                f'Estado inconsistente da migração {migracao.VERSAO}: '
                + '; '.join(problemas)
            )

        status.append(StatusMigracao(
            versao=migracao.VERSAO,
            nome=migracao.NOME,
            aplicada=aplicada,
        ))

    return status


def obter_status(database: Database) -> list[StatusMigracao]:
    with _conexao(database):
        _habilitar_chaves_estrangeiras(database)
        return _obter_status_conectado(database)


def banco_sqlite(caminho: str | Path, *, somente_leitura: bool) -> SqliteDatabase:
    caminho_resolvido = Path(caminho).resolve()
    if not caminho_resolvido.is_file():
        raise FileNotFoundError(f'Banco SQLite não encontrado: {caminho_resolvido}')

    if somente_leitura:
        nome_banco = f'file:{caminho_resolvido.as_posix()}?mode=ro'
        return SqliteDatabase(
            nome_banco,
            uri=True,
            pragmas={'foreign_keys': 1},
        )

    return SqliteDatabase(
        caminho_resolvido,
        pragmas={'foreign_keys': 1},
    )


def consultar_status(caminho: str | Path) -> list[StatusMigracao]:
    database = banco_sqlite(caminho, somente_leitura=True)
    return obter_status(database)


def executar_migracoes(database: Database) -> list[StatusMigracao]:
    with _conexao(database):
        _habilitar_chaves_estrangeiras(database)

        # Detecta conflitos antes de realizar qualquer escrita.
        _obter_status_conectado(database)

        with database.atomic():
            if not _tabela_existe(database, 'schema_migrations'):
                database.execute_sql(SQL_TABELA_MIGRACOES)

            status = _obter_status_conectado(database)
            for item, migracao in zip(status, MIGRACOES, strict=True):
                if item.aplicada:
                    continue

                migracao.aplicar(database)
                database.execute_sql(
                    '''
                    INSERT INTO schema_migrations (versao, nome, checksum)
                    VALUES (?, ?, ?)
                    ''',
                    (migracao.VERSAO, migracao.NOME, migracao.CHECKSUM),
                )

            return _obter_status_conectado(database)
