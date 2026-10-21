import unittest
from unittest.mock import patch

from app.services import catalogo


class CatalogoTestCase(unittest.TestCase):
    def setUp(self):
        self.cache_original = catalogo._cache_acoes
        self.expiracao_original = catalogo._cache_expira_em
        catalogo._cache_acoes = None
        catalogo._cache_expira_em = 0.0

    def tearDown(self):
        catalogo._cache_acoes = self.cache_original
        catalogo._cache_expira_em = self.expiracao_original

    def test_normaliza_somente_acoes_validas_do_mercado_padrao(self):
        item = {
            'type': 'stock',
            'subType': 'stock',
            'stock': ' petr4 ',
            'name': ' Petrobras PN ',
            'close': '31.25',
            'change': '-1.5',
            'volume': '1000',
        }

        self.assertEqual(
            catalogo._normalizar_acao(item),
            {
                'ticker': 'PETR4',
                'nome': 'Petrobras PN',
                'preco': 31.25,
                'variacao': -1.5,
                'volume': 1000,
            },
        )
        self.assertIsNone(catalogo._normalizar_acao({**item, 'stock': 'PETR4F'}))
        self.assertIsNone(catalogo._normalizar_acao({**item, 'type': 'fund'}))

    def test_reutiliza_catalogo_durante_o_ttl(self):
        acoes = ({'ticker': 'PETR4', 'nome': 'Petrobras'},)

        with (
            patch.object(catalogo, '_carregar_catalogo', return_value=acoes) as carregar,
            patch.object(catalogo.time, 'monotonic', return_value=100.0),
        ):
            primeiro = catalogo.obter_catalogo_acoes()
            segundo = catalogo.obter_catalogo_acoes()

        self.assertIs(primeiro, segundo)
        carregar.assert_called_once_with()
        self.assertEqual(
            catalogo._cache_expira_em,
            100.0 + catalogo.CATALOGO_TTL_SEGUNDOS,
        )

    def test_reutiliza_cache_expirado_se_atualizacao_falhar(self):
        cache_anterior = ({'ticker': 'VALE3', 'nome': 'Vale'},)
        catalogo._cache_acoes = cache_anterior
        catalogo._cache_expira_em = 10.0

        with (
            patch.object(catalogo, '_carregar_catalogo', side_effect=ValueError),
            patch.object(catalogo.time, 'monotonic', return_value=20.0),
        ):
            resultado = catalogo.obter_catalogo_acoes()

        self.assertIs(resultado, cache_anterior)

    def test_informa_indisponibilidade_quando_nao_existe_cache(self):
        with (
            patch.object(catalogo, '_carregar_catalogo', side_effect=ValueError),
            patch.object(catalogo.time, 'monotonic', return_value=20.0),
        ):
            with self.assertRaises(catalogo.ErroCatalogoAtivos):
                catalogo.obter_catalogo_acoes()

    def test_nao_repete_chamada_externa_durante_janela_de_erro(self):
        with (
            patch.object(catalogo, '_carregar_catalogo', side_effect=ValueError) as carregar,
            patch.object(catalogo.time, 'monotonic', return_value=20.0),
        ):
            for _ in range(2):
                with self.assertRaises(catalogo.ErroCatalogoAtivos):
                    catalogo.obter_catalogo_acoes()

        carregar.assert_called_once_with()
        self.assertEqual(
            catalogo._cache_expira_em,
            20.0 + catalogo.CATALOGO_RETRY_SEGUNDOS,
        )

    def test_ordena_exato_prefixo_de_ticker_e_correspondencias_no_nome(self):
        acoes = (
            {'ticker': 'XPTO3', 'nome': 'Vale Holdings'},
            {'ticker': 'VALE5', 'nome': 'Vale Preferencial'},
            {'ticker': 'ZZZZ3', 'nome': 'Companhia Vale Industrial'},
            {'ticker': 'VALE3', 'nome': 'Vale ON'},
        )

        with patch.object(catalogo, 'obter_catalogo_acoes', return_value=acoes):
            resultado = catalogo.buscar_sugestoes('vale', limite=4)

        self.assertEqual(
            [item['ticker'] for item in resultado],
            ['VALE3', 'VALE5', 'XPTO3', 'ZZZZ3'],
        )

    def test_ticker_exato_vem_antes_de_nome_com_o_mesmo_texto(self):
        acoes = (
            {'ticker': 'ABCD3', 'nome': 'VALE3 Participações'},
            {'ticker': 'VALE3', 'nome': 'Vale ON'},
        )

        with patch.object(catalogo, 'obter_catalogo_acoes', return_value=acoes):
            resultado = catalogo.buscar_sugestoes('vale3', limite=2)

        self.assertEqual(
            [item['ticker'] for item in resultado],
            ['VALE3', 'ABCD3'],
        )

    def test_busca_por_nome_ignora_acentos_e_respeita_limite(self):
        acoes = (
            {'ticker': 'SMTO3', 'nome': 'São Martinho'},
            {'ticker': 'ABCD3', 'nome': 'Sao Carlos'},
        )

        with patch.object(catalogo, 'obter_catalogo_acoes', return_value=acoes):
            resultado = catalogo.buscar_sugestoes('são', limite=1)

        self.assertEqual(resultado, [{'ticker': 'ABCD3', 'nome': 'Sao Carlos'}])


if __name__ == '__main__':
    unittest.main()
