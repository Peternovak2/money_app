import unittest
from unittest.mock import patch


try:
    from fastapi import HTTPException
    from app.routes.api.api import sugestoes_ativos
    from app.services.catalogo import ErroCatalogoAtivos
except ModuleNotFoundError:
    HTTPException = None
    sugestoes_ativos = None
    ErroCatalogoAtivos = None


@unittest.skipIf(sugestoes_ativos is None, 'dependências FastAPI não disponíveis')
class SugestoesApiTestCase(unittest.TestCase):
    def test_repassa_consulta_normalizada_e_limite(self):
        esperado = [{'ticker': 'VALE3', 'nome': 'Vale'}]

        with patch(
            'app.routes.api.api.buscar_sugestoes',
            return_value=esperado,
        ) as buscar:
            resultado = sugestoes_ativos('  vale  ', 3)

        self.assertEqual(resultado, esperado)
        buscar.assert_called_once_with('vale', 3)

    def test_rejeita_consulta_vazia_ou_com_controle(self):
        for consulta in ('   ', 'vale\n'):
            with self.subTest(consulta=consulta):
                with self.assertRaises(HTTPException) as contexto:
                    sugestoes_ativos(consulta, 8)
                self.assertEqual(contexto.exception.status_code, 400)

    def test_converte_falha_do_catalogo_em_503(self):
        with patch(
            'app.routes.api.api.buscar_sugestoes',
            side_effect=ErroCatalogoAtivos,
        ):
            with self.assertRaises(HTTPException) as contexto:
                sugestoes_ativos('vale', 8)

        self.assertEqual(contexto.exception.status_code, 503)


if __name__ == '__main__':
    unittest.main()
