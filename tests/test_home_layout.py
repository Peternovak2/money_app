import json
import shutil
import subprocess
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.services.utils.formatar import formatar_numero, formatar_variacao, formatar_ticker_historico
from app.services import populares


RAIZ = Path(__file__).resolve().parents[1]


def renderizar_home(usuario=None, rankings=None, noticias=None, carteira=None, componentes=False):
    env = Environment(loader=FileSystemLoader(RAIZ / 'app/templates'),
                      autoescape=select_autoescape())
    env.filters['formatar_numero'] = formatar_numero
    env.filters['formatar_variacao'] = formatar_variacao
    acoes = [dict(ticker=f'TEST{i}', nome='Empresa Teste', preco=10,
                  variacao=1, volume=1000) for i in range(5)]
    html = env.get_template('index.html').render(
        asset_version='test', usuario=usuario, csrf_token='csrf-ficticio',
        rankings_mercado=rankings if rankings is not None else dict(
            altas=acoes, baixas=acoes, mais_negociadas=acoes),
        noticias=noticias or [],
        carteira_home=carteira if carteira is not None else dict(estado="anonimo" if usuario is None else "indisponivel", ativos=[]),
    )
    if componentes or carteira is not None:
        html += env.get_template('components/home_market_panels.html').render(usuario=usuario, carteira_home=carteira or dict(estado='anonimo', ativos=[]))
        html += env.get_template('components/home_mercados.html').render()
    return BeautifulSoup(html, 'html.parser')


class HomeLayoutTestCase(unittest.TestCase):
    def test_home_simplificada_sem_paineis_ou_carregamentos_exclusivos(self):
        pagina = renderizar_home()
        self.assertEqual([e['id'] for e in pagina.select('.home-content > section')],
                         ['dashboard', 'mercado', 'acoes-destaque', 'explorar'])
        for ident in ('mercados', 'minha-carteira', 'desempenho-setor', 'cambio-commodities'):
            self.assertIsNone(pagina.find(id=ident))
        for recurso in ('home-panels.js', 'home-mercados.js', 'home-panels.css'):
            self.assertNotIn(recurso, str(pagina))
        self.assertIsNotNone(pagina.select_one('link[href^="/static/css/home-mercados.css"]'))
        self.assertIsNotNone(pagina.select_one('#dashboard-ibov-canvas'))
        self.assertIsNotNone(pagina.select_one('#noticias'))

    def test_carteira_estados_sem_sessao_vazia_e_indisponivel(self):
        pagina = renderizar_home(componentes=True)
        painel = pagina.select_one('#minha-carteira')
        self.assertEqual([link['href'] for link in painel.select('a')], ['/login', '/cadastro'])
        for estado, mensagem in (
            ('vazio', 'Você ainda não acompanha nenhum ativo.'),
            ('indisponivel', 'Acompanhamento temporariamente indisponível'),
        ):
            pagina = renderizar_home(usuario={'nome': 'Pessoa'}, carteira=dict(estado=estado, ativos=[]))
            painel = pagina.select_one('#minha-carteira')
            self.assertIn(mensagem, painel.get_text())
            self.assertEqual(painel.select_one('a')['href'], '#formBusca')
            self.assertFalse(painel.select('canvas, li'))

    def test_painel_de_indices_tem_catalogo_controlado_sem_alterar_cards_iniciais(self):
        pagina = renderizar_home()
        secao = pagina.select_one('#indices')
        botao = secao.select_one('#indices-add-toggle')
        self.assertEqual(botao['aria-expanded'], 'false')
        painel = secao.find(id=botao['aria-controls'])
        self.assertTrue(painel.has_attr('hidden'))
        self.assertIsNotNone(painel.select_one('label[for="indices-picker-search"]'))
        self.assertEqual(len(secao.select('#indices-carousel [data-index-symbol]')), 1)
        opcoes = painel.select('[data-index-option]')
        simbolos = [opcao['data-index-option'] for opcao in opcoes if opcao['data-index-option']]
        self.assertEqual(len(simbolos), len(set(simbolos)))
        for simbolo in simbolos:
            self.assertEqual(formatar_ticker_historico(simbolo), simbolo)
        for opcao in opcoes:
            if not opcao['data-index-option']:
                self.assertTrue(opcao.has_attr('disabled'))
                self.assertIn('Indisponível', opcao.get_text())
        self.assertIn('^DJI', simbolos)
        self.assertIn('^GDAXI', simbolos)

    def test_status_unico_do_pregao_preserva_fallback_sem_legenda(self):
        pagina = renderizar_home()
        cabecalho = pagina.select_one('#dashboard > .dashboard-heading')
        self.assertIsNotNone(cabecalho.select_one('#panorama-titulo'))
        indicador = cabecalho.select_one('.market-session')
        self.assertEqual(len(pagina.select('.market-session')), 1)
        self.assertEqual(indicador.get_text(strip=True), 'Status indisponível')
        self.assertEqual(indicador['role'], 'status')
        self.assertEqual(len(indicador.select('.market-session__dot')), 1)
        self.assertEqual(indicador.select_one('.market-session__dot')['aria-hidden'], 'true')
        self.assertFalse(indicador.select('li, a, .market-session__legend, .market-session__chip'))
        self.assertFalse(indicador.select('[aria-current], [aria-pressed], .is-active'))
        self.assertIsNone(pagina.select_one('#dashboard-ibov .market-session'))
        self.assertIsNone(pagina.select_one('#noticias .market-session'))

    def test_noticias_na_lateral_preservam_ordem_texto_links_e_datas(self):
        noticias = [dict(
            titulo=f'Notícia {i} <script>alert(1)</script>',
            url=f'https://agenciabrasil.ebc.com.br/economia/{i}',
            fonte='Agência Brasil',
            publicado_em=datetime(2026, 11, 10 - i, tzinfo=timezone.utc),
            imagem='https://agenciabrasil.ebc.com.br/foto.jpg' if i == 0 else None,
        ) for i in range(4)]
        pagina = renderizar_home(noticias=noticias)
        painel = pagina.select_one('.dashboard-grid > #noticias')
        self.assertIsNotNone(painel)
        self.assertEqual(len(pagina.select('#noticias')), 1)
        self.assertIsNone(pagina.select_one('.home-content > #noticias'))
        self.assertEqual(painel.select_one('h2').get_text(), 'Economia em destaque')
        links = painel.select('a.news-card')
        self.assertEqual(len(links), 4)
        self.assertEqual([el.select_one('h3').get_text() for el in links],
                         [item['titulo'] for item in noticias[:4]])
        self.assertFalse(painel.select('script'))
        self.assertEqual(len(painel.select('.news-card--lead')), 1)
        self.assertEqual(len(painel.select('.news-card__media--empty')), 3)
        for link, noticia in zip(links, noticias):
            self.assertEqual(link['href'], noticia['url'])
            self.assertEqual(link['target'], '_blank')
            self.assertEqual(set(link['rel']), {'noopener', 'noreferrer'})
            self.assertEqual(link.select_one('time')['datetime'],
                             noticia['publicado_em'].isoformat())
            self.assertIn(noticia['fonte'], link.get_text())
        self.assertEqual(links[0].select_one('img')['src'], noticias[0]['imagem'])

    def test_noticias_indisponiveis_preservam_grafico_e_ancora(self):
        pagina = renderizar_home()
        self.assertIsNotNone(pagina.select_one('#noticias [role="status"]'))
        self.assertFalse(pagina.select('#noticias a.news-card'))
        self.assertIsNotNone(pagina.select_one('#dashboard-ibov-canvas'))
        self.assertEqual(len(pagina.select('#indices')), 1)

    def test_topbar_contem_marca_pesquisa_e_conta_sem_duplicar_ids(self):
        for usuario in (None, {'nome': 'Pessoa Teste'}):
            with self.subTest(usuario=usuario):
                pagina = renderizar_home(usuario)
                barra = pagina.select_one('.home-topbar')
                self.assertIsNotNone(barra.select_one('a.home-brand[href="/"]'))
                self.assertIsNotNone(barra.select_one('#formBusca #tickerInput'))
                self.assertIsNotNone(barra.select_one('#homeMenuToggle'))
                self.assertIsNone(pagina.select_one('.home-header .logo'))
                self.assertIsNotNone(pagina.select_one('#sidebarToggle'))
                ids = [item['id'] for item in pagina.select('[id]')]
                self.assertEqual(len(ids), len(set(ids)))
                if usuario:
                    self.assertIsNotNone(barra.select_one('a[href="/conta"]'))
                    self.assertEqual(barra.select_one('form[action="/logout"] input')['value'], 'csrf-ficticio')
                else:
                    self.assertIsNotNone(barra.select_one('a[href="/login"]'))
                    self.assertIsNotNone(barra.select_one('a[href="/cadastro"]'))

    def test_composicao_preserva_rankings_conteudos_e_destinos(self):
        pagina = renderizar_home()
        grade = pagina.select_one('.dashboard-grid')
        self.assertIsNotNone(grade.select_one('#dashboard-ibov-canvas'))
        self.assertIsNone(grade.select_one('#mercado'))
        self.assertIsNotNone(grade.select_one('.dashboard-left #indices'))
        self.assertEqual(pagina.select_one('#panorama-titulo').get_text(), 'Mercado Hoje')
        self.assertEqual([el.get('id') for el in pagina.select('.home-content > section')][:3], ['dashboard', 'mercado', 'acoes-destaque'])
        grade = pagina.select_one('#mercado')
        self.assertEqual(len(grade.select('.market-panel')), 2)
        self.assertEqual(len(grade.select('.market-panel tbody tr')), 10)
        for destino in ('/mercado/altas', '/mercado/baixas'):
            self.assertIsNotNone(grade.select_one(f'a[href="{destino}"]'))
        self.assertEqual(len(pagina.select('#acoes-destaque tbody tr')), 5)
        for ident in ('indices', 'explorar', 'noticias-titulo'):
            self.assertIsNotNone(pagina.find(id=ident))
        for link in pagina.select('a[href^="#"]'):
            self.assertIsNotNone(pagina.find(id=link['href'][1:]))

    def test_icones_ibovespa_e_setas_sem_flash_antes_do_javascript(self):
        pagina = renderizar_home()
        self.assertIsNotNone(pagina.select_one('#dashboard-index-icon svg'))
        self.assertIsNotNone(pagina.select_one('[data-index-symbol="^BVSP"] svg'))
        self.assertFalse(pagina.select('[data-index-symbol]:not([data-index-symbol="^BVSP"]) svg'))
        for botao in pagina.select('[data-indices-scroll]'):
            self.assertTrue(botao.has_attr('hidden'))
            self.assertTrue(botao.has_attr('disabled'))
    def test_cabecalho_do_grafico_expoe_nome_ticker_e_periodo_sem_variacao_absoluta(self):
        pagina = renderizar_home()
        cabecalho = pagina.select_one('.dashboard-chart-card__header')
        self.assertEqual(cabecalho.select_one('#dashboard-titulo').get_text(), 'Ibovespa')
        self.assertEqual(cabecalho.select_one('.dashboard-chart-card__exchange').get_text(), 'IBOV')
        self.assertIsNone(cabecalho.select_one('#dashboard-ibov-change-abs'))
        self.assertIsNotNone(cabecalho.select_one('#dashboard-index-icon svg'))
        self.assertEqual(cabecalho.select_one('#dashboard-ibov-period-label').get_text(), '6 meses')
        self.assertNotIn('pontos', cabecalho.get_text())
        self.assertEqual(len(cabecalho.select('[data-ibov-periodo]')), 5)
    def test_carrossel_unico_acima_do_grafico_com_tickers_curtos(self):
        pagina = renderizar_home()
        esquerda = pagina.select_one('.dashboard-left')
        self.assertEqual([item.get('id') for item in esquerda.find_all(recursive=False)],
                         ['indices', 'dashboard-ibov'])
        self.assertEqual(len(pagina.select('#indices')), 1)
        self.assertEqual([item.get_text() for item in pagina.select('.index-summary__ticker')],
                         ['IBOV'])
        self.assertEqual(len(pagina.select('[data-index-direction]')), 1)
        self.assertTrue(all(item.has_attr('hidden') for item in pagina.select('[data-index-value]')))
        self.assertIn('sr-only', pagina.select_one('#indices-titulo')['class'])
        self.assertEqual([item['tabindex'] for item in pagina.select('[data-index-symbol]')],
                         ['0'])
    def test_abas_paineis_e_filtros_tem_associacoes_acessiveis(self):
        pagina = renderizar_home(componentes=True)
        abas = pagina.select('#mercados [role="tab"]')
        self.assertEqual(len(abas), 8)
        for indice, aba in enumerate(abas):
            painel = pagina.find(id=aba['aria-controls'])
            self.assertEqual(painel['aria-labelledby'], aba['id'])
            self.assertEqual(aba['aria-selected'], 'true' if indice == 0 else 'false')
            self.assertEqual(painel.has_attr('hidden'), indice != 0)
        self.assertEqual(len(pagina.select('[data-market-filters] button')), 6)
        for categoria in ('commodities', 'moedas', 'etfs', 'titulos', 'fundos', 'cripto'):
            painel = pagina.find(id=f'mercado-painel-{categoria}')
            self.assertIn('Dados desta categoria ainda não disponíveis.', painel.get_text())
            self.assertFalse(painel.select('a'))
        self.assertEqual(len(pagina.select('button[data-index-symbol]')), 1)
        self.assertEqual(len(pagina.select('button[data-index-symbol][aria-pressed=true]')), 1)

    def test_rankings_renderizam_cinco_ordenados_sem_completar_dados_ausentes(self):
        for quantidade in (0, 2, 8):
            with self.subTest(quantidade=quantidade):
                acoes = tuple(
                    dict(ticker=f'{prefixo}{i}', nome='Empresa Teste', preco=10,
                         variacao=sinal * i, volume=1000)
                    for prefixo, sinal in (('ALTA', 1), ('BAIXA', -1))
                    for i in range(1, quantidade + 1)
                )
                with patch.object(populares, 'obter_catalogo_acoes', return_value=acoes):
                    rankings = populares.buscar_rankings_mercado()
                pagina = renderizar_home(rankings=rankings)
                for tipo, prefixo, sinal in (('altas', 'ALTA', '+'), ('baixas', 'BAIXA', '-')):
                    painel = pagina.select_one(f'[aria-labelledby="{tipo}-titulo"]')
                    links = painel.select('tbody a')
                    esperados = list(range(quantidade, max(0, quantidade - 5), -1))
                    self.assertEqual([link.select_one('strong').get_text() for link in links],
                                     [f'{prefixo}{i}' for i in esperados])
                    self.assertEqual([link['href'] for link in links],
                                     [f'/ativo/{prefixo}{i}' for i in esperados])
                    self.assertEqual([el.get_text() for el in painel.select('.variation')],
                                     [f'{sinal}{i},00%' for i in esperados])
                    self.assertIsNotNone(painel.select_one(f'a[href="/mercado/{tipo}"]'))
                    if quantidade == 0:
                        self.assertIsNotNone(painel.select_one('[role="status"]'))

    def test_modo_sem_sidebar_preserva_navegacao_e_estrutura_da_topbar(self):
        pagina = renderizar_home()
        self.assertIn('home-sidebar-disabled', pagina.body['class'])
        barra = pagina.select_one('.home-topbar')
        grupo = barra.select_one('.home-topbar__brand-group')
        botao = grupo.select_one('#homeMenuToggle')
        self.assertEqual(botao['aria-controls'], 'homePrimaryNav')
        self.assertEqual(botao['aria-expanded'], 'false')
        menu = pagina.find(id=botao['aria-controls'])
        self.assertEqual([link['href'] for link in menu.select('a')],
                         ['/', '#mercado', '#explorar'])
        self.assertEqual([el.get('id') for el in barra.find_all(recursive=False)],
                         [None, 'formBusca', None])

    @unittest.skipUnless(shutil.which('node'), 'Node.js não disponível')
    def test_menu_abre_com_foco_e_preserva_foco_ao_mudar_viewport(self):
        resultado = subprocess.run(
            ['node', str(RAIZ / 'tests/home_navegacao_interacoes.cjs')],
            capture_output=True, text=True, cwd=RAIZ,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node.js não disponível')
    def test_interacoes_reais_do_script_de_mercados(self):
        pagina = renderizar_home(componentes=True)
        raiz = pagina.select_one('[data-markets]')
        fixture = {
            'abas': [dict(id=el['id'], category=el['data-category'],
                          controls=el['aria-controls']) for el in raiz.select('[role="tab"]')],
            'paineis': [el['id'] for el in raiz.select('[role="tabpanel"]')],
            'filtros': [dict(region=el['data-region'], text=el.get_text())
                        for el in raiz.select('[data-market-filters] button')],
        }
        resultado = subprocess.run(
            ['node', str(RAIZ / 'tests/home_mercados_interacoes.cjs')],
            input=json.dumps(fixture), capture_output=True, text=True, cwd=RAIZ,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

    def test_scroll_reveal_exclui_dashboard_e_preserva_conteudo_sem_javascript(self):
        pagina = renderizar_home()
        alvos = pagina.select('.home-body .home-content > .home-section:not(.home-dashboard)')
        self.assertEqual([secao['id'] for secao in alvos],
                         ['mercado', 'acoes-destaque', 'explorar'])
        self.assertFalse(pagina.select('.home-scroll-entering'))
        self.assertTrue(all(not secao.has_attr('hidden') for secao in alvos))
        self.assertIsNotNone(pagina.select_one('script[src^="/static/js/home-scroll.js"]'))

    @unittest.skipUnless(shutil.which('node'), 'Node.js não disponível')
    def test_scroll_reveal_execucao_unica_foco_movimento_reduzido_e_fallbacks(self):
        resultado = subprocess.run(
            ['node', str(RAIZ / 'tests/home_scroll_interacoes.cjs')],
            capture_output=True, text=True, cwd=RAIZ,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)


    @unittest.skipUnless(shutil.which('node'), 'Node.js não disponível')
    def test_selecao_indices_periodos_concorrencia_erros_e_carrossel(self):
        resultado = subprocess.run(
            ['node', str(RAIZ / 'tests/home_indices_interacoes.cjs')],
            capture_output=True, text=True, encoding='utf-8', cwd=RAIZ,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node.js não disponível')
    def test_rolagem_nativa_preservada_com_e_sem_movimento_reduzido(self):
        resultado = subprocess.run(
            ['node', str(RAIZ / 'tests/home_vertical_scroll_interacoes.cjs')],
            capture_output=True, text=True, encoding='utf-8', cwd=RAIZ,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

if __name__ == '__main__':
    unittest.main()
