import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.api.api import router
from app.services import catalogo
from test_home_layout import renderizar_home


class BuscaAvancadaTestCase(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.acoes = (
            dict(ticker='PETR4', nome='Petrobras PN', volume=300,
                 logo='https://icons.brapi.dev/icons/PETR4.svg'),
            dict(ticker='PETR3', nome='Petrobras ON', volume=100),
            dict(ticker='VALE3', nome='Vale ON', volume=200,
                 logo='https://untrusted.example/logo.svg'),
        )
        self.mock_catalogo = patch.object(catalogo, 'obter_catalogo_acoes', return_value=self.acoes)
        self.mock_catalogo.start()
        self.addCleanup(self.mock_catalogo.stop)

    def test_descoberta_por_volume_e_contrato_compativel(self):
        resposta = self.client.get('/api/ativos/descoberta?limite=2')
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([item['ticker'] for item in resposta.json()], ['PETR4', 'VALE3'])
        self.assertEqual(resposta.json()[0], dict(ticker='PETR4', nome='Petrobras PN',
                         tipo='acao', logo_url='https://icons.brapi.dev/icons/PETR4.svg'))
        self.assertIsNone(resposta.json()[1]['logo_url'])

    def test_ticker_nome_e_parte_do_ticker_nas_duas_categorias(self):
        for categoria in ('todos', 'acao'):
            for consulta, esperado in (('PETR4', ['PETR4']), ('PETR', ['PETR3', 'PETR4']),
                                      ('petrobras', ['PETR3', 'PETR4']), ('ETR', ['PETR3', 'PETR4'])):
                with self.subTest(categoria=categoria, consulta=consulta):
                    resposta = self.client.get('/api/ativos/sugestoes', params=dict(q=consulta, categoria=categoria))
                    self.assertEqual(resposta.status_code, 200)
                    self.assertEqual([item['ticker'] for item in resposta.json()], esperado)
                    self.assertTrue(all(item['tipo'] == 'acao' for item in resposta.json()))

    def test_categorias_nao_suportadas_limites_e_entradas_invalidas(self):
        for endpoint in ('descoberta', 'sugestoes?q=PETR&'):
            separador = '?' if '?' not in endpoint else ''
            for parametro in ('categoria=fii', 'categoria=etf', 'limite=100'):
                resposta = self.client.get(f'/api/ativos/{endpoint}{separador}{parametro}')
                self.assertEqual(resposta.status_code, 422)
        for q in ('', '   ', 'PETR\n'):
            self.assertIn(self.client.get('/api/ativos/sugestoes', params={'q': q}).status_code, (400, 422))

    def test_erro_do_catalogo_nao_inventa_descoberta(self):
        with patch.object(catalogo, 'obter_catalogo_acoes', side_effect=catalogo.ErroCatalogoAtivos):
            self.assertEqual(self.client.get('/api/ativos/descoberta').status_code, 503)
            self.assertEqual(self.client.get('/api/ativos/sugestoes?q=PETR').status_code, 503)

    def test_origens_de_imagens_sao_restritas(self):
        for logo in ('http://icons.brapi.dev/icons/PETR4.svg', 'javascript:alert(1)',
                     'https://icons.brapi.dev.evil.example/x.svg', 'https://icons.brapi.dev:444/x.svg',
                     'https://user:pass@icons.brapi.dev/x.svg', 'https://icons.brapi.dev/x.svg?token=x',
                     'https://icons.brapi.dev/x.svg#x', 'https://[', None):
            with self.subTest(logo=logo):
                self.assertIsNone(catalogo._logo_busca_permitido(logo))
        self.assertEqual(catalogo._logo_busca_permitido(self.acoes[0]['logo']), self.acoes[0]['logo'])

    def test_template_tem_um_unico_painel_e_categorias_reais(self):
        pagina = renderizar_home()
        self.assertEqual(len(pagina.select('#painelSugestoes')), 1)
        self.assertEqual([item['data-search-category'] for item in pagina.select('[data-search-category]')], ['todos', 'acao'])
        self.assertEqual(pagina.select_one('#fecharBusca')['type'], 'button')
        self.assertIsNotNone(pagina.select_one('#tickerInput[role=combobox]'))
        self.assertIsNotNone(pagina.select_one('#sugestoesAtivos[role=listbox]'))

    @unittest.skipUnless(shutil.which('node'), 'Node.js indisponível')
    def test_interacoes_do_javascript_real(self):
        resultado = subprocess.run(['node', 'tests/home_busca_interacoes.cjs'],
                                   cwd=Path(__file__).resolve().parents[1], capture_output=True,
                                   text=True, encoding='utf-8')
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)


if __name__ == '__main__':
    unittest.main()
