import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from peewee import SqliteDatabase
from starlette.middleware.sessions import SessionMiddleware

from app.database import Favorito, Usuario
from app.migrations.runner import executar_migracoes
from app.services import carteira
from app.services.auth import obter_usuario_logado
from app.services.catalogo import ErroCatalogoAtivos
from test_home_layout import renderizar_home


class CarteiraHomeTestCase(unittest.TestCase):
    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory()
        self.caminho = Path(self.temporario.name) / 'teste.db'
        self.banco = SqliteDatabase(self.caminho, pragmas={'foreign_keys': 1})
        self.originais = {modelo: modelo._meta.database for modelo in (Usuario, Favorito)}
        self.banco.bind([Usuario, Favorito])
        self.banco.create_tables([Usuario])
        self.usuario = Usuario.create(nome='Pessoa teste', email='a@example.test', senha_hash='teste')
        self.outro = Usuario.create(nome='Outra pessoa', email='b@example.test', senha_hash='teste')
        self.addCleanup(self.restaurar)

    def restaurar(self):
        self.banco.close()
        for modelo, original in self.originais.items():
            modelo.bind(original, bind_refs=False, bind_backrefs=False)
        self.temporario.cleanup()

    def buscar(self, usuario_id):
        return carteira.buscar_carteira_home(usuario_id, caminho_banco=self.caminho)

    def popular(self):
        executar_migracoes(self.banco)
        for i in range(6):
            Favorito.create(usuario=self.usuario, ticker=f'TEST{i}')
        Favorito.create(usuario=self.outro, ticker='OUTRO3')

    def test_sem_sessao_nao_consulta_banco_nem_catalogo(self):
        with patch.object(carteira, 'consultar_status') as status, patch.object(carteira, 'obter_catalogo_acoes') as catalogo:
            self.assertEqual(self.buscar(None), {'estado': 'anonimo', 'ativos': []})
        status.assert_not_called()
        catalogo.assert_not_called()

    def test_migracao_pendente_nao_vira_lista_vazia_nem_altera_banco(self):
        self.banco.close()
        antes = self.caminho.read_bytes()
        self.assertEqual(self.buscar(self.usuario.id)['estado'], 'indisponivel')
        self.assertEqual(self.caminho.read_bytes(), antes)
        self.assertNotIn('favoritos', self.banco.get_tables())

    def test_banco_ausente_nao_e_criado(self):
        ausente = self.caminho.parent / 'ausente.db'
        self.assertEqual(carteira.buscar_carteira_home(self.usuario.id, caminho_banco=ausente)['estado'], 'indisponivel')
        self.assertFalse(ausente.exists())

    def test_quatro_mais_recentes_isolados_por_usuario_sem_mudar_modelos(self):
        self.popular()
        acoes = tuple(dict(ticker=f'TEST{i}', nome=f'Empresa {i}', preco=10+i,
                           variacao=-1 if i == 5 else 2, logo=None) for i in range(6))
        self.banco.close()
        antes = hashlib.sha256(self.caminho.read_bytes()).hexdigest()
        with patch.object(carteira, 'obter_catalogo_acoes', return_value=acoes) as catalogo:
            resultado = self.buscar(self.usuario.id)
        self.assertEqual([acao['ticker'] for acao in resultado['ativos']], ['TEST5', 'TEST4', 'TEST3', 'TEST2'])
        self.assertEqual(resultado['ativos'][0]['preco'], 15)
        self.assertEqual(resultado['ativos'][0]['variacao'], -1)
        catalogo.assert_called_once_with()
        self.assertIs(Favorito._meta.database, self.banco)
        self.assertEqual(hashlib.sha256(self.caminho.read_bytes()).hexdigest(), antes)
        pagina = renderizar_home(usuario={'nome': 'Pessoa teste'}, carteira=resultado)
        self.assertEqual(len(pagina.select('#minha-carteira .home-watchlist__list > li')), 4)
        self.assertEqual([a['href'] for a in pagina.select('#minha-carteira .financial-asset')],
                         [f'/ativo/TEST{i}' for i in (5, 4, 3, 2)])
        self.assertIn('R$ 15,00', pagina.select_one('#minha-carteira').get_text())
        self.assertIn('-1,00%', pagina.select_one('#minha-carteira').get_text())

    def test_lista_vazia_nao_consulta_catalogo(self):
        executar_migracoes(self.banco)
        with patch.object(carteira, 'obter_catalogo_acoes') as catalogo:
            self.assertEqual(self.buscar(self.usuario.id), {'estado': 'vazio', 'ativos': []})
        catalogo.assert_not_called()

    def test_falha_de_cotacao_preserva_tickers_e_links_sem_numeros_ficticios(self):
        self.popular()
        with patch.object(carteira, 'obter_catalogo_acoes', side_effect=ErroCatalogoAtivos):
            resultado = self.buscar(self.usuario.id)
        self.assertEqual(resultado['estado'], 'sucesso')
        self.assertTrue(all(acao['preco'] is None and acao['variacao'] is None for acao in resultado['ativos']))
        pagina = renderizar_home(usuario={'nome': 'Pessoa'}, carteira=resultado)
        self.assertEqual(len(pagina.select('#minha-carteira a')), 4)
        self.assertNotIn('R$', pagina.select_one('#minha-carteira').get_text())

    def test_home_usa_sessao_e_ignora_user_id_da_query_string(self):
        self.popular()
        with patch.dict(os.environ, {'SECRET_KEY': 'chave-somente-teste'}):
            from app import main
        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key='chave-somente-teste')
        app.get('/')(main.home)

        @app.get('/__test__/autenticar')
        def autenticar(request: Request):
            request.session['user_id'] = self.usuario.id
            return {'ok': True}

        def autenticar_em_leitura(request):
            # Fecha a conexão do worker do TestClient na mesma thread em que abriu.
            with self.banco.connection_context():
                return obter_usuario_logado(request)

        with (
            patch.object(carteira, 'DB_PATH', self.caminho),
            patch.object(carteira, 'obter_catalogo_acoes', side_effect=AssertionError('Home nao deve consultar favoritos')),
            patch.object(main, 'obter_usuario_logado', side_effect=autenticar_em_leitura),
            patch.object(main, 'buscar_rankings_mercado', return_value=dict(altas=[], baixas=[], mais_negociadas=[])),
            patch.object(main, 'buscar_noticias_home', return_value=[]),
            TestClient(app) as client,
        ):
            anonimo = client.get('/')
            self.assertNotIn('id="minha-carteira"', anonimo.text)
            client.get('/__test__/autenticar')
            resposta = client.get('/', params={'user_id': self.outro.id})
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn('/ativo/TEST5', resposta.text)
        self.assertNotIn('/ativo/OUTRO3', resposta.text)


if __name__ == '__main__':
    unittest.main()
