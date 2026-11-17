import unittest
from unittest.mock import patch

from app.services import populares
from app.services.catalogo import ErroCatalogoAtivos


class RankingsMercadoTestCase(unittest.TestCase):
    def test_monta_rankings_com_catalogo_compartilhado(self):
        acoes = (
            {'ticker': 'ALTA3', 'nome': 'Alta', 'preco': 10, 'variacao': 5, 'volume': 50},
            {'ticker': 'BAIX3', 'nome': 'Baixa', 'preco': 8, 'variacao': -4, 'volume': 20},
            {'ticker': 'VOLM3', 'nome': 'Volume', 'preco': 12, 'variacao': 1, 'volume': 100},
        )

        with patch.object(populares, 'obter_catalogo_acoes', return_value=acoes):
            resultado = populares.buscar_rankings_mercado()

        self.assertEqual(resultado['altas'][0]['ticker'], 'ALTA3')
        self.assertEqual(resultado['baixas'][0]['ticker'], 'BAIX3')
        self.assertEqual(resultado['mais_negociadas'][0]['ticker'], 'VOLM3')

    def test_falha_do_catalogo_preserva_resultado_vazio(self):
        with patch.object(
            populares,
            'obter_catalogo_acoes',
            side_effect=ErroCatalogoAtivos,
        ):
            resultado = populares.buscar_rankings_mercado()

        self.assertEqual(resultado['altas'], [])
        self.assertEqual(resultado['baixas'], [])
        self.assertEqual(resultado['mais_negociadas'], [])

    def test_ranking_completo_reutiliza_catalogo_e_ordena_movimentos(self):
        acoes = (
            {'ticker': 'ALTA3', 'nome': 'Alta', 'preco': 10, 'variacao': 2, 'volume': 50},
            {'ticker': 'MAIS3', 'nome': 'Mais alta', 'preco': 12, 'variacao': 5, 'volume': 80},
            {'ticker': 'BAIX3', 'nome': 'Baixa', 'preco': 8, 'variacao': -4, 'volume': 20},
        )

        with patch.object(populares, 'obter_catalogo_acoes', return_value=acoes):
            altas = populares.buscar_ranking_movimento('altas')
            baixas = populares.buscar_ranking_movimento('baixas')

        self.assertEqual(
            [acao['ticker'] for acao in altas['itens']],
            ['MAIS3', 'ALTA3'],
        )
        self.assertEqual(
            [acao['ticker'] for acao in baixas['itens']],
            ['BAIX3'],
        )

    def test_ranking_completo_trata_indisponibilidade_do_catalogo(self):
        with patch.object(
            populares,
            'obter_catalogo_acoes',
            side_effect=ErroCatalogoAtivos,
        ):
            resultado = populares.buscar_ranking_movimento('altas')

        self.assertEqual(resultado['itens'], [])
        self.assertTrue(resultado['indisponivel'])

    def test_ranking_completo_rejeita_tipo_desconhecido(self):
        with self.assertRaises(ValueError):
            populares.buscar_ranking_movimento('volume')


if __name__ == '__main__':
    unittest.main()
