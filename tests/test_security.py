import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from peewee import SqliteDatabase
from starlette.middleware.sessions import SessionMiddleware

from app.database import Usuario
from app.routes import auth
from app.services.security import (
    configuracao_cookie_sessao,
    exigir_csrf,
    exigir_usuario_api,
    obter_token_csrf,
)


RAIZ_PROJETO = Path(__file__).resolve().parents[1]


def _aplicacao_cookie(configuracao):
    app = FastAPI()
    app.add_middleware(SessionMiddleware, **configuracao)

    @app.get('/definir-sessao')
    def definir_sessao(request: Request):
        request.session['teste'] = 'ok'
        return {'ok': True}

    return app


class ConfiguracaoCookieTestCase(unittest.TestCase):
    def test_cookie_de_desenvolvimento_nao_exige_https(self):
        configuracao = configuracao_cookie_sessao({
            'SECRET_KEY': 'segredo-de-teste',
            'APP_ENV': 'development',
        })

        with TestClient(_aplicacao_cookie(configuracao)) as client:
            resposta = client.get('/definir-sessao')

        cookie = resposta.headers['set-cookie'].lower()
        self.assertNotIn('; secure', cookie)
        self.assertIn('httponly', cookie)
        self.assertIn('samesite=lax', cookie)

    def test_cookie_de_producao_exige_https(self):
        configuracao = configuracao_cookie_sessao({
            'SECRET_KEY': 'segredo-de-teste',
            'APP_ENV': 'production',
            'SESSION_HTTPS_ONLY': 'false',
        })

        with TestClient(_aplicacao_cookie(configuracao)) as client:
            resposta = client.get('/definir-sessao')

        self.assertIn('; secure', resposta.headers['set-cookie'].lower())

    def test_desenvolvimento_pode_habilitar_cookie_https(self):
        configuracao = configuracao_cookie_sessao({
            'SECRET_KEY': 'segredo-de-teste',
            'APP_ENV': 'development',
            'SESSION_HTTPS_ONLY': 'true',
        })

        self.assertTrue(configuracao['https_only'])

    def test_secret_key_continua_obrigatoria(self):
        with self.assertRaises(ValueError):
            configuracao_cookie_sessao({})


class SegurancaHttpTestCase(unittest.TestCase):
    def setUp(self):
        self.diretorio_temporario = tempfile.TemporaryDirectory()
        caminho_banco = Path(self.diretorio_temporario.name) / 'security-test.db'
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
                nome='Usuária de Teste',
                email='seguranca@example.com',
                senha_hash='hash-de-teste',
            )

        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key='segredo-de-teste')
        app.include_router(auth.router)

        @app.get('/__test__/autenticar/{user_id}')
        def autenticar_teste(request: Request, user_id: int):
            request.session['user_id'] = user_id
            return {'csrf_token': obter_token_csrf(request)}

        @app.get('/__test__/sessao-invalida')
        def sessao_invalida(request: Request):
            request.session['user_id'] = 'invalido'
            return {'ok': True}

        @app.get('/__test__/sessao-antiga')
        def sessao_antiga(request: Request):
            request.session.update({
                'user_id': 999,
                'csrf_token': 'token-antigo',
                'legado': 'valor-antigo',
            })
            return {'ok': True}

        @app.get('/__test__/estado-sessao')
        def estado_sessao(request: Request):
            return dict(request.session)

        @app.get('/__test__/privada')
        def privada(usuario=Depends(exigir_usuario_api)):
            return {'user_id': usuario.id}

        @app.post('/__test__/escrita')
        def escrita_privada(
            usuario=Depends(exigir_usuario_api),
            _csrf=Depends(exigir_csrf),
        ):
            return {'user_id': usuario.id}

        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        if not self.banco_teste.is_closed():
            self.banco_teste.close()
        self.banco_original.bind([Usuario])
        self.diretorio_temporario.cleanup()

    def _autenticar(self):
        resposta = self.client.get(f'/__test__/autenticar/{self.usuario.id}')
        self.assertEqual(resposta.status_code, 200)
        return resposta.json()['csrf_token']

    def test_sessao_valida_autoriza_api_privada(self):
        self._autenticar()

        resposta = self.client.get('/__test__/privada')

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()['user_id'], self.usuario.id)

    def test_api_privada_rejeita_ausencia_de_sessao(self):
        resposta = self.client.get('/__test__/privada')

        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.json()['detail'], 'Autenticação necessária')

    def test_api_privada_ignora_user_id_fornecido_pelo_navegador(self):
        resposta = self.client.get(
            f'/__test__/privada?user_id={self.usuario.id}'
        )

        self.assertEqual(resposta.status_code, 401)

    def test_api_privada_rejeita_identificador_de_sessao_invalido(self):
        self.client.get('/__test__/sessao-invalida')

        resposta = self.client.get('/__test__/privada')

        self.assertEqual(resposta.status_code, 401)

    def test_csrf_ausente_e_invalido_sao_rejeitados(self):
        self._autenticar()

        ausente = self.client.post('/__test__/escrita')
        invalido = self.client.post(
            '/__test__/escrita',
            headers={'X-CSRF-Token': 'token-incorreto'},
        )

        self.assertEqual(ausente.status_code, 403)
        self.assertEqual(invalido.status_code, 403)

    def test_csrf_valido_autoriza_escrita(self):
        token = self._autenticar()

        resposta = self.client.post(
            '/__test__/escrita',
            headers={'X-CSRF-Token': token},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()['user_id'], self.usuario.id)

    def test_login_limpa_estado_anterior_e_renova_csrf(self):
        self.client.get('/__test__/sessao-antiga')

        with patch.object(auth, 'autenticar', return_value=self.usuario):
            resposta = self.client.post(
                '/login',
                data={'email': self.usuario.email, 'senha': 'senha-de-teste'},
                follow_redirects=False,
            )

        estado = self.client.get('/__test__/estado-sessao').json()
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(estado['user_id'], self.usuario.id)
        self.assertNotEqual(estado['csrf_token'], 'token-antigo')
        self.assertNotIn('legado', estado)

    def test_logout_exige_csrf_e_preserva_sessao_quando_rejeitado(self):
        token = self._autenticar()

        ausente = self.client.post('/logout', follow_redirects=False)
        invalido = self.client.post(
            '/logout',
            data={'csrf_token': 'token-incorreto'},
            follow_redirects=False,
        )
        estado = self.client.get('/__test__/estado-sessao').json()

        self.assertEqual(ausente.status_code, 403)
        self.assertEqual(invalido.status_code, 403)
        self.assertEqual(estado['user_id'], self.usuario.id)
        self.assertEqual(estado['csrf_token'], token)

    def test_logout_com_csrf_valido_limpa_sessao(self):
        token = self._autenticar()

        resposta = self.client.post(
            '/logout',
            data={'csrf_token': token},
            follow_redirects=False,
        )

        estado = self.client.get('/__test__/estado-sessao').json()
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.headers['location'], '/')
        self.assertEqual(estado, {})


class CsrfFrontendTestCase(unittest.TestCase):
    def test_formularios_de_logout_incluem_token_csrf(self):
        for caminho in (
            'app/templates/index.html',
            'app/templates/ativo.html',
            'app/templates/conta.html',
        ):
            with self.subTest(caminho=caminho):
                template = (RAIZ_PROJETO / caminho).read_text(encoding='utf-8')
                pagina = BeautifulSoup(template, 'html.parser')
                formulario = pagina.select_one('form[action="/logout"]')
                token = formulario.select_one(
                    'input[type="hidden"][name="csrf_token"]'
                )

                self.assertIsNotNone(token)
                self.assertEqual(token.get('value'), '{{ csrf_token }}')


if __name__ == '__main__':
    unittest.main()
