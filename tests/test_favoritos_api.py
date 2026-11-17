import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from peewee import SqliteDatabase
from starlette.middleware.sessions import SessionMiddleware

from app.database import Usuario, Favorito
from app.migrations.runner import executar_migracoes
from app.routes.api import paineis
from app.services.security import exigir_usuario_api


class FavoritosApiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'teste.db'
        self.db = SqliteDatabase(self.path, pragmas={'foreign_keys': 1})
        self.originais = {m:m._meta.database for m in (Usuario, Favorito)}
        self.db.bind([Usuario, Favorito])
        self.db.create_tables([Usuario])
        self.user = Usuario.create(nome='Teste', email='a@example.test', senha_hash='hash')
        self.outro = Usuario.create(nome='Outro', email='b@example.test', senha_hash='hash')
        executar_migracoes(self.db)
        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key='teste')
        app.include_router(paineis.router)
        self.app = app
        app.dependency_overrides[exigir_usuario_api] = lambda: SimpleNamespace(id=self.user.id)
        @app.get('/__test__/csrf')
        def csrf(request: Request):
            request.session['csrf_token'] = 'csrf-teste'
            return {}
        self.client = TestClient(app)
        self.client.get('/__test__/csrf')
        self.patch = patch.object(paineis, 'DB_PATH', self.path)
        self.patch.start()

    def tearDown(self):
        self.client.close()
        self.patch.stop()
        self.db.close()
        for model, db in self.originais.items():
            model.bind(db, bind_refs=False, bind_backrefs=False)
        self.temp.cleanup()

    def test_adicionar_idempotente_remover_e_isolar(self):
        headers = {'X-CSRF-Token':'csrf-teste'}
        with patch.object(paineis, 'obter_catalogo_acoes', return_value=({'ticker':'PETR4'},)):
            for _ in range(2):
                self.assertEqual(self.client.post('/api/conta/favoritos/PETR4', headers=headers).status_code, 200)
        self.assertEqual(Favorito.select().count(), 1)
        Favorito.create(usuario=self.outro, ticker='PETR4')
        self.assertEqual(self.client.delete('/api/conta/favoritos/PETR4', headers=headers).status_code, 200)
        self.assertEqual(Favorito.select().count(), 1)
        self.assertEqual(Favorito.get().usuario_id, self.outro.id)

    def test_csrf_e_validacao_catalogo(self):
        self.assertEqual(self.client.post('/api/conta/favoritos/PETR4').status_code, 403)
        with patch.object(paineis, 'obter_catalogo_acoes', return_value=()):
            self.assertEqual(self.client.post('/api/conta/favoritos/PETR4', headers={'X-CSRF-Token':'csrf-teste'}).status_code, 503)
        self.assertEqual(Favorito.select().count(), 0)
