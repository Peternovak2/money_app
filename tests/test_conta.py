import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient
from peewee import SqliteDatabase
from starlette.middleware.sessions import SessionMiddleware

from app.database import Usuario
from app.routes import conta


RAIZ_PROJETO = Path(__file__).resolve().parents[1]


class ContaHttpTestCase(unittest.TestCase):
    def setUp(self):
        self.diretorio_temporario = tempfile.TemporaryDirectory()
        caminho_banco = Path(self.diretorio_temporario.name) / 'conta-test.db'
        self.banco_original = Usuario._meta.database
        self.banco_teste = SqliteDatabase(
            caminho_banco,
            pragmas={'foreign_keys': 1},
            thread_safe=False,
            check_same_thread=False,
        )
        self.banco_teste.bind([Usuario])

        with self.banco_teste:
            self.banco_teste.create_tables([Usuario])
            self.usuario = Usuario.create(
                nome='Maria Investidora',
                email='maria@example.com',
                senha_hash='hash-secreto-nao-expor',
            )

        app = FastAPI()
        app.state.asset_version = 'test'
        app.add_middleware(SessionMiddleware, secret_key='segredo-de-teste')
        app.include_router(conta.router)

        @app.get('/__test__/sessao/{user_id}')
        def criar_sessao(request: Request, user_id: int):
            request.session['user_id'] = user_id
            return PlainTextResponse('ok')

        @app.get('/__test__/sessao-invalida')
        def criar_sessao_invalida(request: Request):
            request.session['user_id'] = 'invalido'
            return PlainTextResponse('ok')

        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        if not self.banco_teste.is_closed():
            self.banco_teste.close()
        self.banco_original.bind([Usuario])
        self.diretorio_temporario.cleanup()

    def _autenticar(self, user_id=None):
        identificador = self.usuario.id if user_id is None else user_id
        resposta = self.client.get(f'/__test__/sessao/{identificador}')
        self.assertEqual(resposta.status_code, 200)

    def test_usuario_autenticado_acessa_nome_e_email(self):
        self._autenticar()

        resposta = self.client.get('/conta')

        self.assertEqual(resposta.status_code, 200)
        self.assertIn('Maria Investidora', resposta.text)
        self.assertIn('maria@example.com', resposta.text)
        self.assertNotIn('hash-secreto-nao-expor', resposta.text)
        self.assertNotIn('senha_hash', resposta.text)

    def test_pagina_privada_nao_pode_ser_armazenada_em_cache(self):
        self._autenticar()

        resposta = self.client.get('/conta')

        self.assertEqual(
            resposta.headers['cache-control'],
            'no-store, no-cache, must-revalidate, max-age=0',
        )
        self.assertEqual(resposta.headers['pragma'], 'no-cache')
        self.assertEqual(resposta.headers['expires'], '0')

    def test_usuario_nao_autenticado_e_redirecionado(self):
        resposta = self.client.get('/conta', follow_redirects=False)

        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.headers['location'], '/login')

    def test_usuario_excluido_nao_consegue_acessar(self):
        self._autenticar(user_id=999_999)

        resposta = self.client.get('/conta', follow_redirects=False)

        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.headers['location'], '/login')

    def test_identificador_de_sessao_invalido_e_rejeitado(self):
        self.client.get('/__test__/sessao-invalida')

        resposta = self.client.get('/conta', follow_redirects=False)

        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.headers['location'], '/login')


class ContaFrontendTestCase(unittest.TestCase):
    def test_headers_autenticados_ligam_resumo_a_minha_conta(self):
        for caminho in (
            'app/templates/index.html',
            'app/templates/ativo.html',
        ):
            with self.subTest(caminho=caminho):
                template = (RAIZ_PROJETO / caminho).read_text(encoding='utf-8')
                pagina = BeautifulSoup(template, 'html.parser')
                acesso = pagina.select_one('a.usuario-resumo[href="/conta"]')

                self.assertIsNotNone(acesso)
                self.assertIsNotNone(acesso.select_one('.usuario-avatar'))
                self.assertIsNotNone(acesso.select_one('.usuario-nome'))
                self.assertIsNotNone(pagina.select_one('form[action="/logout"]'))

    def test_recursos_futuros_nao_sao_controles_falsos(self):
        template = (
            RAIZ_PROJETO / 'app/templates/conta.html'
        ).read_text(encoding='utf-8')
        pagina = BeautifulSoup(template, 'html.parser')
        recursos = pagina.select('.conta-navegacao__item--futuro')

        self.assertEqual(len(recursos), 4)
        self.assertEqual(template.count('Em planejamento'), 1)
        for recurso in recursos:
            self.assertEqual(recurso.get('aria-disabled'), 'true')
            self.assertIsNone(recurso.find('a'))
            self.assertIsNone(recurso.find('button'))

    def test_template_usa_estrutura_semantica_e_dados_limitados(self):
        template = (
            RAIZ_PROJETO / 'app/templates/conta.html'
        ).read_text(encoding='utf-8')
        pagina = BeautifulSoup(template, 'html.parser')

        self.assertIsNotNone(pagina.select_one('main.conta-page'))
        self.assertIsNotNone(pagina.select_one('nav[aria-label="Seções da conta"]'))
        self.assertIsNotNone(pagina.select_one('section#perfil'))
        self.assertIsNotNone(pagina.select_one('dl.conta-dados'))
        self.assertIn('{{ usuario.nome }}', template)
        self.assertIn('{{ usuario.email }}', template)
        self.assertNotIn('senha_hash', template)


if __name__ == '__main__':
    unittest.main()
