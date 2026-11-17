import unittest
from unittest.mock import PropertyMock, patch

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient
from yfinance.exceptions import YFPricesMissingError, YFRateLimitError, YFTzMissingError

from app.routes.api.api import router
from app.services.utils.formatar import formatar_ticker_historico


class HistoricoApiTestCase(unittest.TestCase):
    def setUp(self):
        # Usa o router real, sem importar app.main ou executar o startup do banco.
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.patch_ticker = patch('app.services.informacoes.yf.Ticker')
        self.criar_ticker = self.patch_ticker.start()
        self.addCleanup(self.patch_ticker.stop)
        self.ativo = self.criar_ticker.return_value
        self.ativo.info = {'quoteType': 'EQUITY'}
        self.ativo.history.return_value = pd.DataFrame(
            {'Open': [100.0], 'High': [105.0], 'Low': [99.0],
             'Close': [103.0], 'Volume': [1000]},
            index=pd.to_datetime(['2026-11-06']),
        )

    def test_acoes_e_ibovespa_preservam_simbolo_e_contrato_json(self):
        for entrada, consulta, retorno in (
            ('PETR4', 'PETR4.SA', 'PETR4'),
            ('VALE3', 'VALE3.SA', 'VALE3'),
            ('petr4.sa', 'PETR4.SA', 'PETR4'),
            ('%5EBVSP', '^BVSP', '^BVSP'),
            ('%5Ebvsp', '^BVSP', '^BVSP'),
            ('%5EGSPC', '^GSPC', '^GSPC'),
            ('%5ENDX', '^NDX', '^NDX'),
            ('%5EN225', '^N225', '^N225'),
            ('%5EFTSE', '^FTSE', '^FTSE'),
            ('%5EDJI', '^DJI', '^DJI'),
            ('%5EGDAXI', '^GDAXI', '^GDAXI'),
            ('000001.SS', '000001.SS', '000001.SS'),
        ):
            with self.subTest(ticker=entrada):
                self.criar_ticker.reset_mock()
                resposta = self.client.get(f'/api/{entrada}/historico?periodo=6mo')
                self.assertEqual(resposta.status_code, 200)
                self.criar_ticker.assert_called_once_with(consulta)
                self.ativo.history.assert_called_once_with(
                    period='6mo', interval='1d', actions=False,
                    auto_adjust=False, raise_errors=True,
                )
                self.assertEqual(resposta.json(), {
                    'ticker': retorno, 'periodo': '6mo', 'intervalo': '1d',
                    'pontos': [{'time': '2026-11-06', 'open': 100.0,
                                'high': 105.0, 'low': 99.0, 'close': 103.0,
                                'volume': 1000}],
                })

    def test_identificadores_invalidos_nao_consultam_provedor(self):
        for entrada in ('%5EINVALID', '%5EBVSP.SA', '%5EBVSPevil',
                        'PETR4%20', '%20', 'PETR4%0A', '.SA',
                        'PETR4..SA', 'PETR4%3F', 'PETR4%3D', 'A' * 40):
            with self.subTest(ticker=entrada):
                resposta = self.client.get(f'/api/{entrada}/historico')
                self.assertEqual(resposta.status_code, 400)
                self.assertEqual(resposta.json(), {'detail': 'Ticker inválido'})
        self.criar_ticker.assert_not_called()

    def test_periodo_invalido_nao_consulta_provedor(self):
        resposta = self.client.get('/api/%5EBVSP/historico?periodo=2d')
        self.assertEqual(resposta.status_code, 400)
        self.criar_ticker.assert_not_called()

    def test_periodos_e_intervalos_do_ibovespa(self):
        for periodo, intervalo in (
            ('1mo', '1d'), ('3mo', '1d'), ('6mo', '1d'),
            ('1y', '1d'), ('5y', '1wk'), ('max', '1mo'),
        ):
            with self.subTest(periodo=periodo):
                resposta = self.client.get(f'/api/%5EBVSP/historico?periodo={periodo}')
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.json()['intervalo'], intervalo)
                self.assertEqual(self.ativo.history.call_args.kwargs['interval'], intervalo)

    def test_indice_existente_sem_precos_retorna_lista_vazia(self):
        self.ativo.info = {'quoteType': 'INDEX'}
        for resultado in (pd.DataFrame(), None):
            with self.subTest(resultado=type(resultado).__name__):
                self.ativo.history.return_value = resultado
                resposta = self.client.get('/api/%5EBVSP/historico')
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.json(), {
                    'ticker': '^BVSP', 'periodo': '6mo',
                    'intervalo': '1d', 'pontos': [],
                })

    def test_excecao_de_precos_ausentes_valida_existencia_do_ativo(self):
        self.ativo.history.side_effect = YFPricesMissingError('^BVSP', 'period=6mo')
        self.ativo.info = {'quoteType': 'INDEX'}
        resposta = self.client.get('/api/%5EBVSP/historico')
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()['pontos'], [])

    def test_ativo_inexistente_retorna_404(self):
        self.ativo.info = {}
        for erro in (None, YFPricesMissingError('INVALIDO.SA', ''),
                     YFTzMissingError('INVALIDO.SA')):
            with self.subTest(erro=type(erro).__name__):
                self.ativo.history.side_effect = erro
                self.ativo.history.return_value = pd.DataFrame()
                resposta = self.client.get('/api/INVALIDO/historico')
                self.assertEqual(resposta.status_code, 404)
                self.assertEqual(resposta.json(), {'detail': 'Ativo não encontrado'})

    def test_falhas_do_provedor_retornam_502_e_nao_404(self):
        for erro in (TimeoutError('timeout'), ConnectionError('offline'), YFRateLimitError()):
            with self.subTest(erro=type(erro).__name__):
                self.ativo.history.side_effect = erro
                resposta = self.client.get('/api/%5EBVSP/historico')
                self.assertEqual(resposta.status_code, 502)
                self.assertEqual(resposta.json(), {
                    'detail': 'Não foi possível consultar o histórico no momento',
                })

    def test_falha_ao_validar_ativo_nao_vira_404(self):
        self.ativo.history.return_value = pd.DataFrame()
        with patch.object(type(self.ativo), 'info', new_callable=PropertyMock,
                          side_effect=ConnectionError('offline'), create=True):
            resposta = self.client.get('/api/%5EBVSP/historico')
        self.assertEqual(resposta.status_code, 502)

    def test_falha_na_criacao_do_cliente_retorna_502(self):
        self.criar_ticker.side_effect = ConnectionError('offline')
        resposta = self.client.get('/api/%5EBVSP/historico')
        self.assertEqual(resposta.status_code, 502)

    def test_resposta_sem_ohlc_retorna_502(self):
        self.ativo.history.return_value = pd.DataFrame(
            {'Close': [103.0]}, index=pd.to_datetime(['2026-11-06']),
        )
        resposta = self.client.get('/api/%5EBVSP/historico')
        self.assertEqual(resposta.status_code, 502)


class TickerHistoricoTestCase(unittest.TestCase):
    def test_preserva_simbolos_qualificados_existentes(self):
        for ticker in ('PETR4.SA', 'BRK-B', 'BTC-USD'):
            with self.subTest(ticker=ticker):
                self.assertEqual(formatar_ticker_historico(ticker), ticker)

    def test_rejeita_tipos_invalidos_e_entrada_vazia(self):
        for ticker in (None, 123, '', '^', '^^BVSP', '^BVSP\n', 'PETRſ'):
            with self.subTest(ticker=ticker):
                with self.assertRaises(ValueError):
                    formatar_ticker_historico(ticker)


if __name__ == '__main__':
    unittest.main()
