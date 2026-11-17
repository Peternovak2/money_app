import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup
from app.routes import mercado
from app.services import catalogo, populares
from test_home_layout import renderizar_home


class FinancialAssetsTestCase(unittest.TestCase):
    def test_tres_tabelas_reutilizam_um_catalogo_com_logos_validados(self):
        itens = [dict(type='stock', subType='stock', stock=f'TEST{i}', name=f'Empresa {i}',
                      close=10 + i, change=i if i <= 12 else -i, volume=i * 100,
                      logo='https://icons.brapi.dev/icons/PETR4.svg' if i % 3 == 0
                      else 'https://untrusted.example/logo.svg' if i % 3 == 1 else None)
                 for i in range(1, 25)]
        with (patch.object(catalogo, '_cache_acoes', None),
              patch.object(catalogo, '_cache_expira_em', 0),
              patch.object(catalogo, '_buscar_lista_brapi', return_value=itens) as fonte):
            home = renderizar_home(rankings=populares.buscar_rankings_mercado())
            self.assertEqual(len(home.select('#acoes-destaque .financial-asset')), 5)
            self.assertIsNotNone(home.select_one('#market-session-status [data-session-label]'))
            self.assertIsNotNone(home.select_one('script[src^="/static/js/market-session.js"]'))
            for tipo in ('altas', 'baixas'):
                ranking = populares.buscar_ranking_movimento(tipo, pagina=2, tamanho_pagina=10)
                pagina = BeautifulSoup(mercado.templates.env.get_template('ranking.html').render(
                    asset_version='test', usuario=None, ranking=ranking), 'html.parser')
                self.assertEqual(pagina.h1.get_text(), f'Maiores {tipo}')
                self.assertEqual(len(pagina.select('tbody tr')), 2)
                self.assertEqual([el.get_text() for el in pagina.select('.ranking-position')], ['11', '12'])
                self.assertEqual(pagina.select_one('.ranking-count').get_text(), '12 ativos')
                self.assertEqual(len(pagina.select('.ranking-action a')), 2)
                self.assertIsNotNone(pagina.select_one('a[rel=prev][href="?page=1&page_size=10"]'))
                self.assertEqual([el['value'] for el in pagina.select('select[name=page_size] option')], ['10', '20', '50'])
                self.assertIsNotNone(pagina.select_one('form.ranking-page-size button[type=submit]'))
                self.assertIsNotNone(pagina.select_one('script[src^="/static/js/asset-logos.js"]'))
                for identidade in pagina.select('.financial-asset'):
                    self.assertTrue(identidade['href'].startswith('/ativo/TEST'))
                    self.assertTrue(identidade.select_one('.financial-asset__ticker').get_text().startswith('TEST'))
                for img in pagina.select('[data-asset-logo]'):
                    self.assertTrue(img['src'].startswith('https://icons.brapi.dev/'))
                    self.assertEqual(img['width'], '36')
                    self.assertEqual(img['height'], '36')
            fonte.assert_called_once_with()  # Nenhuma chamada por linha, logo ou página.
            self.assertTrue(all(img['src'].startswith('https://icons.brapi.dev/') for img in home.select('[data-asset-logo]')))
            self.assertTrue(any(not el.select('img') for el in home.select('#acoes-destaque .financial-asset__logo')))

    @unittest.skipUnless(shutil.which('node'), 'Node.js indisponível')
    def test_fallback_de_imagens_e_atualizacao_da_sessao(self):
        for arquivo in ('asset_logos_interacoes.cjs', 'market_session_interacoes.cjs'):
            resultado = subprocess.run(['node', f'tests/{arquivo}'],
                                       cwd=Path(__file__).resolve().parents[1], capture_output=True,
                                       text=True, encoding='utf-8')
            self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)


if __name__ == '__main__':
    unittest.main()
