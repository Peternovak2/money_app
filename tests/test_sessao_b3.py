import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfoNotFoundError

from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routes.api.api import router
from app.services import sessao_b3


class SessaoB3TestCase(unittest.TestCase):
    def estado(self, iso):
        return sessao_b3.obter_sessao_b3(datetime.fromisoformat(iso))

    def test_abertura_fechamento_e_fuso_sao_da_sessao_regular(self):
        for instante, esperado in (
            ('2026-11-12T09:59:59-03:00', 'fechado'),
            ('2026-11-12T10:00:00-03:00', 'aberto'),
            ('2026-11-12T17:54:59-03:00', 'aberto'),
            ('2026-11-12T17:55:00-03:00', 'fechado'),
            ('2026-11-12T13:00:00+00:00', 'aberto'),
            ('2026-11-12T12:59:59+00:00', 'fechado'),
            ('2026-11-12T20:00:00-03:00', 'fechado'),
        ):
            with self.subTest(instante=instante):
                resultado = self.estado(instante)
                self.assertEqual(resultado['status'], esperado)
                self.assertEqual(resultado['escopo'], 'sessao_regular_acoes_b3')
                self.assertEqual(resultado['timezone'], 'America/Sao_Paulo')
        self.assertEqual(self.estado('2026-11-12T17:54:59-03:00')['atualizar_em'], 1)

    def test_finais_de_semana_e_feriados_nao_usam_regra_de_dia_util_simples(self):
        for dia in ('2026-11-14', '2026-11-15', '2026-11-20', '2026-11-02',
                    '2026-02-16', '2026-02-17', '2026-12-24', '2026-12-25', '2026-12-31'):
            with self.subTest(dia=dia):
                self.assertEqual(self.estado(f'{dia}T12:00:00-03:00')['status'], 'fechado')

    def test_quarta_feira_de_cinzas_tem_abertura_especial(self):
        self.assertEqual(self.estado('2026-02-18T12:59:59-03:00')['status'], 'fechado')
        self.assertEqual(self.estado('2026-02-18T13:00:00-03:00')['status'], 'aberto')
        self.assertEqual(self.estado('2026-02-18T17:55:00-03:00')['status'], 'fechado')

    def test_sem_grade_validada_nao_inventa_status(self):
        for instante in ('2027-01-04T12:00:00-03:00', '2026-07-09T12:00:00-03:00',
                         '2026-11-12T12:00:00'):
            self.assertEqual(self.estado(instante)['status'], 'indisponivel')

    def test_falhas_de_calendario_e_fuso_preservam_indisponivel(self):
        for erro in (OSError('Falha simulada'), ValueError('JSON inválido'), KeyError('grades')):
            with patch.object(sessao_b3, '_carregar_calendario', side_effect=erro):
                self.assertEqual(self.estado('2026-11-12T12:00:00-03:00')['status'], 'indisponivel')
        with patch.object(sessao_b3, 'ZoneInfo', side_effect=ZoneInfoNotFoundError):
            self.assertEqual(self.estado('2026-11-12T12:00:00-03:00')['status'], 'indisponivel')

    def test_arquivo_invalido_nao_produz_fechado(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / 'calendario.json'
            for conteudo in ('{', '{}', '{"ano":2026,"fontes":[],"feriados":[],"grades":[],"especiais":{}}'):
                caminho.write_text(conteudo, encoding='utf-8')
                sessao_b3._carregar_calendario.cache_clear()
                with patch.object(sessao_b3, 'CAMINHO_CALENDARIO', caminho):
                    self.assertEqual(self.estado('2026-11-12T12:00:00-03:00')['status'], 'indisponivel')
        sessao_b3._carregar_calendario.cache_clear()

    def test_endpoint_sem_cache_http_e_sem_consulta_a_brapi(self):
        app = FastAPI()
        app.include_router(router)
        with patch('app.services.catalogo._buscar_lista_brapi') as brapi, TestClient(app) as client:
            resposta = client.get('/api/mercado/sessao')
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.headers['cache-control'], 'no-store')
        self.assertIn(resposta.json()['status'], ('aberto', 'fechado', 'indisponivel'))
        brapi.assert_not_called()


if __name__ == '__main__':
    unittest.main()
