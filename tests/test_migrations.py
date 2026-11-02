import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from peewee import IntegrityError, SqliteDatabase

import app.database as database_module
from app.database import Favorito, Usuario
from app.migrations.__main__ import main as migrations_main
from app.migrations.runner import (
    SQL_TABELA_MIGRACOES,
    EstadoMigracaoInvalido,
    executar_migracoes,
    obter_status,
)
from app.migrations.versions import v001_criar_favoritos


class MigracoesFavoritosTestCase(unittest.TestCase):
    def setUp(self):
        self.diretorio_temporario = tempfile.TemporaryDirectory()
        self.caminho_banco = (
            Path(self.diretorio_temporario.name) / 'migrations-test.db'
        )
        self.banco_original_usuario = Usuario._meta.database
        self.banco_original_favorito = Favorito._meta.database
        self.banco_teste = SqliteDatabase(
            self.caminho_banco,
            pragmas={'foreign_keys': 1},
            thread_safe=False,
            check_same_thread=False,
        )
        self.banco_teste.bind([Usuario, Favorito])

        with self.banco_teste:
            self.banco_teste.create_tables([Usuario])

    def tearDown(self):
        if not self.banco_teste.is_closed():
            self.banco_teste.close()
        self.banco_original_usuario.bind([Usuario])
        self.banco_original_favorito.bind([Favorito])
        self.diretorio_temporario.cleanup()

    def _nomes_objetos(self, tipo: str) -> set[str]:
        abriu = self.banco_teste.is_closed()
        if abriu:
            self.banco_teste.connect()
        try:
            registros = self.banco_teste.execute_sql(
                'SELECT name FROM sqlite_master WHERE type = ?',
                (tipo,),
            ).fetchall()
            return {registro[0] for registro in registros}
        finally:
            if abriu:
                self.banco_teste.close()

    def _criar_usuario(self, email: str) -> Usuario:
        return Usuario.create(
            nome='Pessoa Investidora',
            email=email,
            senha_hash='hash-de-teste',
        )

    def test_status_cli_e_estritamente_somente_leitura(self):
        conteudo_antes = self.caminho_banco.read_bytes()
        saida = io.StringIO()
        erros = io.StringIO()

        with redirect_stdout(saida), redirect_stderr(erros):
            codigo = migrations_main([
                '--status',
                '--database',
                str(self.caminho_banco),
            ])

        self.assertEqual(codigo, 0)
        self.assertIn('[pendente] 001 criar_favoritos', saida.getvalue())
        self.assertEqual(erros.getvalue(), '')
        self.assertEqual(self.caminho_banco.read_bytes(), conteudo_antes)
        self.assertNotIn('schema_migrations', self._nomes_objetos('table'))
        self.assertNotIn('favoritos', self._nomes_objetos('table'))

    def test_migracao_preserva_usuarios_e_habilita_foreign_keys(self):
        usuario = self._criar_usuario('existente@example.com')

        status = executar_migracoes(self.banco_teste)

        self.assertTrue(status[0].aplicada)
        self.assertEqual(Usuario.get_by_id(usuario.id).email, usuario.email)
        self.assertIn('favoritos', self._nomes_objetos('table'))
        self.assertIn('schema_migrations', self._nomes_objetos('table'))
        self.assertIn(
            'favoritos_usuario_id_ticker',
            self._nomes_objetos('index'),
        )

        self.banco_teste.connect(reuse_if_open=True)
        try:
            foreign_keys = self.banco_teste.execute_sql(
                'PRAGMA foreign_keys'
            ).fetchone()[0]
        finally:
            self.banco_teste.close()
        self.assertEqual(foreign_keys, 1)

    def test_normalizacao_unicidade_integridade_e_isolamento(self):
        executar_migracoes(self.banco_teste)
        primeiro = self._criar_usuario('primeiro@example.com')
        segundo = self._criar_usuario('segundo@example.com')

        favorito = Favorito.create(usuario=primeiro, ticker='  petr4  ')

        self.assertEqual(favorito.ticker, 'PETR4')
        with self.assertRaises(IntegrityError):
            Favorito.create(usuario=primeiro, ticker='petr4')

        favorito_segundo = Favorito.create(usuario=segundo, ticker='PETR4')
        self.assertEqual(favorito_segundo.usuario_id, segundo.id)
        self.assertEqual(
            Favorito.select().where(Favorito.usuario == primeiro).count(),
            1,
        )
        self.assertEqual(
            Favorito.select().where(Favorito.usuario == segundo).count(),
            1,
        )

        with self.assertRaises(IntegrityError):
            Favorito.create(usuario=999_999, ticker='VALE3')

        primeiro.delete_instance()
        self.assertEqual(
            Favorito.select().where(Favorito.usuario == primeiro).count(),
            0,
        )
        self.assertEqual(Favorito.get_by_id(favorito_segundo.id).ticker, 'PETR4')

    def test_ticker_invalido_e_rejeitado_antes_da_gravacao(self):
        executar_migracoes(self.banco_teste)
        usuario = self._criar_usuario('ticker@example.com')

        for ticker in ('', '   ', 'PETR4\n', 'PETR-4', 'A' * 21):
            with self.subTest(ticker=repr(ticker)):
                with self.assertRaises(ValueError):
                    Favorito.create(usuario=usuario, ticker=ticker)

        self.assertEqual(Favorito.select().count(), 0)

    def test_execucao_repetida_nao_recria_estruturas_ou_dados(self):
        executar_migracoes(self.banco_teste)
        usuario = self._criar_usuario('repeticao@example.com')
        Favorito.create(usuario=usuario, ticker='ITUB4')

        status = executar_migracoes(self.banco_teste)

        self.assertTrue(status[0].aplicada)
        self.assertEqual(Favorito.select().count(), 1)
        registros = self.banco_teste.execute_sql(
            'SELECT COUNT(*) FROM schema_migrations WHERE versao = 1'
        ).fetchone()[0]
        self.assertEqual(registros, 1)

    def test_falha_reverte_tabela_indice_e_registro_da_versao(self):
        aplicar_original = v001_criar_favoritos.aplicar

        def aplicar_e_falhar(database):
            aplicar_original(database)
            raise RuntimeError('falha simulada após o DDL')

        with patch.object(
            v001_criar_favoritos,
            'aplicar',
            side_effect=aplicar_e_falhar,
        ):
            with self.assertRaisesRegex(RuntimeError, 'falha simulada'):
                executar_migracoes(self.banco_teste)

        self.assertNotIn('favoritos', self._nomes_objetos('table'))
        self.assertNotIn('schema_migrations', self._nomes_objetos('table'))
        self.assertNotIn(
            'favoritos_usuario_id_ticker',
            self._nomes_objetos('index'),
        )

    def test_versao_desconhecida_e_detectada(self):
        self.banco_teste.connect()
        try:
            self.banco_teste.execute_sql(SQL_TABELA_MIGRACOES)
            self.banco_teste.execute_sql(
                '''
                INSERT INTO schema_migrations (versao, nome, checksum)
                VALUES (999, 'desconhecida', 'checksum')
                '''
            )
        finally:
            self.banco_teste.close()

        with self.assertRaisesRegex(
            EstadoMigracaoInvalido,
            'Versões de migração desconhecidas',
        ):
            obter_status(self.banco_teste)

    def test_registro_de_migracao_inconsistente_e_detectado(self):
        self.banco_teste.connect()
        try:
            self.banco_teste.execute_sql(SQL_TABELA_MIGRACOES)
            self.banco_teste.execute_sql(
                '''
                INSERT INTO schema_migrations (versao, nome, checksum)
                VALUES (?, ?, ?)
                ''',
                (1, v001_criar_favoritos.NOME, 'checksum-incorreto'),
            )
        finally:
            self.banco_teste.close()

        with self.assertRaisesRegex(
            EstadoMigracaoInvalido,
            'Checksum inconsistente',
        ):
            obter_status(self.banco_teste)

    def test_artefatos_sem_registro_sao_detectados(self):
        self.banco_teste.connect()
        try:
            v001_criar_favoritos.aplicar(self.banco_teste)
        finally:
            self.banco_teste.close()

        with self.assertRaisesRegex(
            EstadoMigracaoInvalido,
            'tabela favoritos já existe',
        ):
            obter_status(self.banco_teste)

    def test_startup_continua_sem_executar_migracoes(self):
        outro_caminho = Path(self.diretorio_temporario.name) / 'startup-test.db'
        banco_startup = SqliteDatabase(
            outro_caminho,
            pragmas={'foreign_keys': 1},
        )
        banco_startup.bind([Usuario, Favorito])

        try:
            with patch.object(database_module, 'db', banco_startup):
                database_module.criar_tabelas()

            banco_startup.connect()
            tabelas = {
                item[0]
                for item in banco_startup.execute_sql(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        finally:
            if not banco_startup.is_closed():
                banco_startup.close()
            self.banco_teste.bind([Usuario, Favorito])

        self.assertIn('usuarios', tabelas)
        self.assertNotIn('favoritos', tabelas)
        self.assertNotIn('schema_migrations', tabelas)


if __name__ == '__main__':
    unittest.main()
