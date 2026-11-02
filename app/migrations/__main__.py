import argparse
import sys
from pathlib import Path

from app.database import DB_PATH
from app.migrations.runner import (
    EstadoMigracaoInvalido,
    banco_sqlite,
    consultar_status,
    executar_migracoes,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Consulta ou aplica migrações versionadas do Money App.',
    )
    operacao = parser.add_mutually_exclusive_group(required=True)
    operacao.add_argument(
        '--status',
        action='store_true',
        help='Consulta o estado sem modificar o banco.',
    )
    operacao.add_argument(
        '--apply',
        action='store_true',
        help='Aplica as migrações pendentes.',
    )
    parser.add_argument(
        '--database',
        default=DB_PATH,
        help='Caminho do arquivo SQLite.',
    )
    return parser


def _imprimir_status(status) -> None:
    for item in status:
        situacao = 'aplicada' if item.aplicada else 'pendente'
        print(f'[{situacao}] {item.versao:03d} {item.nome}')


def main(argv: list[str] | None = None) -> int:
    argumentos = _parser().parse_args(argv)
    caminho = Path(argumentos.database).resolve()
    print(f'Banco: {caminho}')

    try:
        if argumentos.status:
            status = consultar_status(caminho)
        else:
            database = banco_sqlite(caminho, somente_leitura=False)
            status = executar_migracoes(database)
    except (EstadoMigracaoInvalido, FileNotFoundError, RuntimeError) as erro:
        print(f'Erro: {erro}', file=sys.stderr)
        return 1

    _imprimir_status(status)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
