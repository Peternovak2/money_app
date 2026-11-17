from hashlib import sha256


VERSAO = 1
NOME = 'criar_favoritos'

COMANDOS_SQL = (
    '''
    CREATE TABLE "favoritos" (
        "id" INTEGER NOT NULL PRIMARY KEY,
        "usuario_id" INTEGER NOT NULL,
        "ticker" VARCHAR(20) NOT NULL
            CHECK (
                length("ticker") BETWEEN 1 AND 20
                AND "ticker" NOT GLOB '*[^A-Z0-9]*'
            ),
        "criado_em" DATETIME NOT NULL,
        FOREIGN KEY ("usuario_id")
            REFERENCES "usuarios" ("id")
            ON DELETE CASCADE
    )
    ''',
    '''
    CREATE UNIQUE INDEX "favoritos_usuario_id_ticker"
    ON "favoritos" ("usuario_id", "ticker")
    ''',
)

CHECKSUM = sha256('\n'.join(COMANDOS_SQL).encode('utf-8')).hexdigest()


def aplicar(database) -> None:
    for comando in COMANDOS_SQL:
        database.execute_sql(comando)


def _objeto_existe(database, tipo: str, nome: str) -> bool:
    cursor = database.execute_sql(
        '''
        SELECT 1
        FROM sqlite_master
        WHERE type = ? AND name = ?
        ''',
        (tipo, nome),
    )
    return cursor.fetchone() is not None


def problemas_estado(database, *, aplicada: bool) -> list[str]:
    tabela_existe = _objeto_existe(database, 'table', 'favoritos')
    indice_existe = _objeto_existe(
        database,
        'index',
        'favoritos_usuario_id_ticker',
    )

    if not aplicada:
        conflitos = []
        if tabela_existe:
            conflitos.append('a tabela favoritos já existe')
        if indice_existe:
            conflitos.append('o índice de favoritos já existe')
        return conflitos

    problemas = []
    if not tabela_existe:
        problemas.append('a tabela favoritos está ausente')
        return problemas
    if not indice_existe:
        problemas.append('o índice único de favoritos está ausente')
        return problemas

    indices = database.execute_sql('PRAGMA index_list("favoritos")').fetchall()
    indice = next(
        (item for item in indices if item[1] == 'favoritos_usuario_id_ticker'),
        None,
    )
    if indice is None or indice[2] != 1:
        problemas.append('o índice de favoritos não é único')
    else:
        colunas = database.execute_sql(
            'PRAGMA index_info("favoritos_usuario_id_ticker")'
        ).fetchall()
        if [item[2] for item in colunas] != ['usuario_id', 'ticker']:
            problemas.append('o índice de favoritos possui colunas inesperadas')

    chaves = database.execute_sql('PRAGMA foreign_key_list("favoritos")').fetchall()
    chave_usuario = next(
        (
            item for item in chaves
            if item[2] == 'usuarios'
            and item[3] == 'usuario_id'
            and item[4] == 'id'
        ),
        None,
    )
    if chave_usuario is None or chave_usuario[6].upper() != 'CASCADE':
        problemas.append('a chave estrangeira de usuário está inconsistente')

    return problemas
