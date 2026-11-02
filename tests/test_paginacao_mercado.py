import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import mercado
from app.services import populares


def _acao(indice, variacao):
    return {
        'ticker': f'ACAO{indice:02d}',
        'nome': f'Ação {indice}',
        'preco': float(indice),
        'variacao': variacao,
        'volume': indice * 100,
    }


class PaginacaoRankingServiceTestCase(unittest.TestCase):
    def test_paginação_preserva_ordem_e_recorta_dez_itens(self):
        acoes = tuple(_acao(indice, indice) for indice in range(1, 26))

        with patch.object(
            populares,
            'obter_catalogo_acoes',
            return_value=acoes,
        ) as obter_catalogo:
            resultado = populares.buscar_ranking_movimento(
                'altas',
                pagina=2,
                tamanho_pagina=10,
            )

        self.assertEqual(len(resultado['itens']), 10)
        self.assertEqual(resultado['itens'][0]['ticker'], 'ACAO15')
        self.assertEqual(resultado['itens'][-1]['ticker'], 'ACAO06')
        self.assertEqual(resultado['paginacao']['total_itens'], 25)
        self.assertEqual(resultado['paginacao']['total_paginas'], 3)
        self.assertEqual(resultado['paginacao']['primeira_posicao'], 11)
        self.assertEqual(resultado['paginacao']['ultima_posicao'], 20)
        obter_catalogo.assert_called_once_with()

    def test_baixas_continuam_ordenadas_da_maior_queda_para_a_menor(self):
        acoes = tuple(_acao(indice, -indice) for indice in range(1, 26))

        with patch.object(populares, 'obter_catalogo_acoes', return_value=acoes):
            resultado = populares.buscar_ranking_movimento(
                'baixas',
                pagina=1,
                tamanho_pagina=20,
            )

        self.assertEqual(resultado['itens'][0]['variacao'], -25)
        self.assertEqual(resultado['itens'][-1]['variacao'], -6)

    def test_aceita_tamanhos_dez_vinte_e_cinquenta(self):
        acoes = tuple(_acao(indice, indice) for indice in range(1, 61))

        for tamanho in populares.TAMANHOS_PAGINA:
            with self.subTest(tamanho=tamanho):
                with patch.object(
                    populares,
                    'obter_catalogo_acoes',
                    return_value=acoes,
                ):
                    resultado = populares.buscar_ranking_movimento(
                        'altas',
                        tamanho_pagina=tamanho,
                    )

                self.assertEqual(len(resultado['itens']), tamanho)
                self.assertEqual(
                    resultado['paginacao']['tamanho_pagina'],
                    tamanho,
                )

    def test_rejeita_parametros_de_paginacao_invalidos(self):
        casos = (
            {'pagina': 0, 'tamanho_pagina': 10},
            {'pagina': True, 'tamanho_pagina': 10},
            {'pagina': 1, 'tamanho_pagina': 15},
        )

        for parametros in casos:
            with self.subTest(parametros=parametros):
                with self.assertRaises(populares.ParametrosPaginacaoInvalidos):
                    populares.buscar_ranking_movimento('altas', **parametros)

    def test_rejeita_pagina_fora_do_intervalo(self):
        acoes = tuple(_acao(indice, indice) for indice in range(1, 26))

        with patch.object(populares, 'obter_catalogo_acoes', return_value=acoes):
            with self.assertRaises(populares.PaginaRankingInexistente):
                populares.buscar_ranking_movimento(
                    'altas',
                    pagina=4,
                    tamanho_pagina=10,
                )

    def test_homepage_continua_limitada_a_cinco_ativos(self):
        acoes = tuple(_acao(indice, indice) for indice in range(1, 16))

        with patch.object(populares, 'obter_catalogo_acoes', return_value=acoes):
            resultado = populares.buscar_rankings_mercado()

        self.assertEqual(len(resultado['altas']), 5)


class PaginacaoRankingHttpTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        app.state.asset_version = 'test'
        app.include_router(mercado.router)
        cls.client = TestClient(app)
        cls.acoes = tuple(
            {
                **_acao(indice, indice),
                'ticker': f'ALTA{indice:02d}',
            }
            for indice in range(1, 61)
        ) + tuple(
            {
                **_acao(indice, -indice),
                'ticker': f'BAIX{indice:02d}',
            }
            for indice in range(1, 61)
        )

    def _get(self, url):
        with (
            patch.object(
                populares,
                'obter_catalogo_acoes',
                return_value=self.acoes,
            ),
            patch.object(mercado, 'obter_usuario_logado', return_value=None),
        ):
            return self.client.get(url)

    def _tickers(self, resposta):
        pagina = BeautifulSoup(resposta.text, 'html.parser')
        return [
            link.get_text(strip=True)
            for link in pagina.select('.ranking-ticker')
        ]

    def test_altas_primeira_pagina_http(self):
        resposta = self._get('/mercado/altas')

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            self._tickers(resposta),
            [f'ALTA{indice:02d}' for indice in range(60, 50, -1)],
        )

    def test_altas_segunda_pagina_converte_page_size_para_inteiro(self):
        resposta = self._get('/mercado/altas?page=2&page_size=10')

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            self._tickers(resposta),
            [f'ALTA{indice:02d}' for indice in range(50, 40, -1)],
        )

    def test_baixas_segunda_pagina_http(self):
        resposta = self._get('/mercado/baixas?page=2&page_size=10')

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            self._tickers(resposta),
            [f'BAIX{indice:02d}' for indice in range(50, 40, -1)],
        )

    def test_tamanhos_vinte_e_cinquenta_por_http(self):
        for tamanho in (20, 50):
            with self.subTest(tamanho=tamanho):
                resposta = self._get(
                    f'/mercado/altas?page=1&page_size={tamanho}'
                )

                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(len(self._tickers(resposta)), tamanho)

    def test_page_size_nao_permitido_retorna_400(self):
        resposta = self._get('/mercado/altas?page=1&page_size=15')

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(
            resposta.json()['detail'],
            'Quantidade por página inválida',
        )

    def test_pagina_zero_retorna_422(self):
        resposta = self._get('/mercado/altas?page=0&page_size=10')

        self.assertEqual(resposta.status_code, 422)

    def test_pagina_fora_do_intervalo_retorna_404(self):
        resposta = self._get('/mercado/baixas?page=99&page_size=10')

        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(
            resposta.json()['detail'],
            'Página do ranking não encontrada',
        )

    def test_altas_e_baixas_usam_botao_voltar_sem_breadcrumb(self):
        for url in ('/mercado/altas', '/mercado/baixas'):
            with self.subTest(url=url):
                resposta = self._get(url)
                pagina = BeautifulSoup(resposta.text, 'html.parser')

                self.assertEqual(resposta.status_code, 200)
                self.assertIsNotNone(pagina.select_one('[data-ranking-back]'))
                self.assertIsNone(pagina.select_one('.ranking-breadcrumb'))


class PaginacaoRankingFrontendTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raiz = Path(__file__).resolve().parents[1]
        cls.template = (raiz / 'app/templates/ranking.html').read_text(
            encoding='utf-8'
        )
        cls.css = (raiz / 'app/static/css/mercado.css').read_text(
            encoding='utf-8'
        )
        cls.javascript = (raiz / 'app/static/js/mercado.js').read_text(
            encoding='utf-8'
        )
        cls.html_renderizado = mercado.templates.env.get_template(
            'ranking.html'
        ).render(
            asset_version='test',
            usuario=None,
            ranking={
                'tipo': 'altas',
                'titulo': 'Maiores altas',
                'descricao': 'Descrição de teste',
                'itens': [_acao(15, 15)],
                'indisponivel': False,
                'paginacao': {
                    'pagina': 2,
                    'tamanho_pagina': 10,
                    'total_itens': 25,
                    'total_paginas': 3,
                    'primeira_posicao': 11,
                    'ultima_posicao': 20,
                    'tem_anterior': True,
                    'tem_proxima': True,
                    'paginas': [1, 2, 3],
                },
            },
        )

    def test_template_expoe_seletor_links_e_pagina_atual(self):
        self.assertIn('name="page_size"', self.template)
        self.assertIn('for tamanho in (10, 20, 50)', self.template)
        self.assertIn('page={{ ranking.paginacao.pagina - 1 }}', self.template)
        self.assertIn('page={{ ranking.paginacao.pagina + 1 }}', self.template)
        self.assertIn('aria-current="page"', self.template)

    def test_pagina_atual_usa_azul_principal(self):
        seletor = '.ranking-pagination__page.is-current'
        inicio = self.css.index(seletor)
        bloco = self.css[inicio:self.css.index('}', inicio)]

        self.assertIn('background: #2563eb;', bloco)

    def test_renderizacao_preserva_url_e_posicao_global(self):
        self.assertIn('?page=1&amp;page_size=10', self.html_renderizado)
        self.assertIn('?page=3&amp;page_size=10', self.html_renderizado)
        self.assertIn('aria-current="page">2</span>', self.html_renderizado)
        self.assertIn('class="ranking-position">11</td>', self.html_renderizado)

    def test_botao_voltar_substitui_breadcrumb(self):
        self.assertNotIn('ranking-breadcrumb', self.template)
        self.assertIn('data-ranking-back', self.template)
        self.assertIn('aria-label="Voltar para a página anterior"', self.template)
        self.assertIn('/static/js/mercado.js', self.template)

    def test_botao_usa_history_back_com_fallback_para_inicio(self):
        self.assertIn('window.history.length > 1', self.javascript)
        self.assertIn('window.history.back()', self.javascript)
        self.assertIn('window.location.assign(fallbackUrl)', self.javascript)


if __name__ == '__main__':
    unittest.main()
