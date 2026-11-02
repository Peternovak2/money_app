import unittest
from unittest.mock import patch

from app.services import noticias


class CacheNoticiasTestCase(unittest.TestCase):
    def setUp(self):
        noticias._cache_noticias = None
        noticias._cache_expira_em = 0.0

    def tearDown(self):
        noticias._cache_noticias = None
        noticias._cache_expira_em = 0.0

    def test_reutiliza_resultado_enquanto_cache_esta_valido(self):
        resultado_remoto = [{'titulo': 'Notícia válida'}]

        with (
            patch.object(
                noticias,
                '_buscar_noticias_remotas',
                return_value=resultado_remoto,
            ) as buscar,
            patch.object(noticias.time, 'monotonic', side_effect=[100, 100, 200]),
        ):
            primeiro = noticias.buscar_noticias_home()
            segundo = noticias.buscar_noticias_home()

        self.assertEqual(primeiro, resultado_remoto)
        self.assertEqual(segundo, resultado_remoto)
        self.assertIsNot(primeiro, segundo)
        buscar.assert_called_once_with()

    def test_atualiza_resultado_depois_da_expiracao(self):
        primeiro_resultado = [{'titulo': 'Primeira notícia'}]
        segundo_resultado = [{'titulo': 'Notícia atualizada'}]

        with (
            patch.object(
                noticias,
                '_buscar_noticias_remotas',
                side_effect=[primeiro_resultado, segundo_resultado],
            ) as buscar,
            patch.object(
                noticias.time,
                'monotonic',
                side_effect=[100, 100, 701, 701],
            ),
        ):
            primeiro = noticias.buscar_noticias_home()
            segundo = noticias.buscar_noticias_home()

        self.assertEqual(primeiro, primeiro_resultado)
        self.assertEqual(segundo, segundo_resultado)
        self.assertEqual(buscar.call_count, 2)

    def test_preserva_ultimo_resultado_valido_durante_falha(self):
        resultado_valido = [{'titulo': 'Notícia preservada'}]

        with (
            patch.object(
                noticias,
                '_buscar_noticias_remotas',
                side_effect=[resultado_valido, TimeoutError],
            ) as buscar,
            patch.object(
                noticias.time,
                'monotonic',
                side_effect=[100, 100, 701, 701],
            ),
        ):
            noticias.buscar_noticias_home()
            resultado = noticias.buscar_noticias_home()

        self.assertEqual(resultado, resultado_valido)
        self.assertEqual(buscar.call_count, 2)
        self.assertEqual(
            noticias._cache_expira_em,
            701 + noticias.NOTICIAS_RETRY_SEGUNDOS,
        )

    def test_evitar_repeticao_imediata_quando_primeira_busca_falha(self):
        with (
            patch.object(
                noticias,
                '_buscar_noticias_remotas',
                side_effect=TimeoutError,
            ) as buscar,
            patch.object(noticias.time, 'monotonic', side_effect=[100, 100, 110]),
        ):
            primeiro = noticias.buscar_noticias_home()
            segundo = noticias.buscar_noticias_home()

        self.assertEqual(primeiro, [])
        self.assertEqual(segundo, [])
        buscar.assert_called_once_with()

    def test_timeout_remoto_permanece_limitado(self):
        self.assertEqual(noticias.AGENCIA_BRASIL_TIMEOUT, 4)


if __name__ == '__main__':
    unittest.main()
