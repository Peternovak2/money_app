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


if __name__ == '__main__':
    unittest.main()
