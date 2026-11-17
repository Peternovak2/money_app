import unittest
from unittest.mock import patch

from app.services import painel_dados as dados


def serie(inicio=100):
    return [{'data': f'2026-10-{i:02d}', 'valor': inicio+i} for i in range(1, 22)]


class PainelDadosTestCase(unittest.TestCase):
    def setUp(self):
        dados._cache.clear()

    def tearDown(self):
        dados._cache.clear()

    def test_macro_cache_unidades_e_falha_isolada(self):
        def carregar(simbolo):
            if simbolo == 'GC=F':
                raise TimeoutError()
            return serie()
        with patch.object(dados, 'serie_diaria', side_effect=carregar) as busca:
            primeiro = dados.buscar_macro()
            self.assertEqual(dados.buscar_macro(), primeiro)
        self.assertEqual(busca.call_count, 5)
        self.assertEqual(primeiro[2]['estado'], 'indisponivel')
        self.assertNotIn('valor', primeiro[2])
        self.assertEqual(primeiro[-1]['unidade'], 'USD por libra')
        self.assertAlmostEqual(primeiro[0]['variacao'], 100*(121/101-1))

    def test_setores_amostra_pesos_e_datas_comuns(self):
        catalogo = [dict(ticker=f'A{i}', setor=cat, volume=i)
                    for cat, _ in dados.SETORES for i in range(3)]
        with patch.object(dados, 'obter_catalogo_acoes', return_value=catalogo), patch.object(dados, 'serie_diaria', return_value=serie()) as busca:
            resultado = dados.buscar_setores()
        self.assertEqual(busca.call_count, 8)
        for item in resultado:
            self.assertEqual(item['membros'], ['A2', 'A1'])
            self.assertEqual(item['estado'], 'disponivel')
            self.assertEqual(item['serie'][0]['valor'], 100)
            self.assertEqual(item['inicio'], '2026-10-01')
            self.assertAlmostEqual(item['variacao'], 100*(121/101-1))

    def test_series_insuficientes_e_catalogo_ausente(self):
        with patch.object(dados, 'obter_catalogo_acoes', side_effect=TimeoutError):
            self.assertTrue(all(i['estado'] == 'indisponivel' for i in dados.buscar_setores()))
        with self.assertRaises(ValueError):
            dados.resumir(serie()[:1])

    def test_falha_em_uma_amostra_nao_invalida_demais_setores(self):
        catalogo = [dict(ticker=f'A{i}', setor=cat, volume=i)
                    for cat, _ in dados.SETORES for i in range(2)]
        with patch.object(dados, 'obter_catalogo_acoes', return_value=catalogo), patch.object(dados, 'serie_diaria', side_effect=[TimeoutError()] + [serie()]*6):
            resultado = dados.buscar_setores()
        self.assertEqual(resultado[0]['estado'], 'indisponivel')
        self.assertTrue(all(i['estado'] == 'disponivel' for i in resultado[1:]))
