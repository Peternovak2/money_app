import unittest
from html.parser import HTMLParser
from pathlib import Path


RAIZ_PROJETO = Path(__file__).resolve().parents[1]


class ElementosPorIdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elementos = {}

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        identificador = atributos.get('id')
        if identificador:
            self.elementos[identificador] = (tag, atributos)


class FrontendBuscaTestCase(unittest.TestCase):
    def test_template_expoe_combobox_e_listbox_acessiveis(self):
        parser = ElementosPorIdParser()
        parser.feed(
            (RAIZ_PROJETO / 'app/templates/index.html').read_text(encoding='utf-8')
        )

        _, campo = parser.elementos['tickerInput']
        _, lista = parser.elementos['sugestoesAtivos']
        _, status = parser.elementos['buscaStatus']

        self.assertEqual(campo['role'], 'combobox')
        self.assertEqual(campo['aria-controls'], 'sugestoesAtivos')
        self.assertEqual(campo['aria-autocomplete'], 'list')
        self.assertEqual(lista['role'], 'listbox')
        self.assertEqual(status['role'], 'status')
        self.assertEqual(status['aria-live'], 'polite')

    def test_javascript_usa_cancelamento_e_dom_seguro(self):
        javascript = (
            RAIZ_PROJETO / 'app/static/js/home.js'
        ).read_text(encoding='utf-8')

        self.assertIn('new AbortController()', javascript)
        self.assertIn('window.setTimeout', javascript)
        self.assertIn('document.createElement', javascript)
        self.assertIn('textContent', javascript)
        self.assertIn('encodeURIComponent', javascript)
        self.assertNotIn('innerHTML', javascript)
        self.assertNotIn('insertAdjacentHTML', javascript)

    def test_atalhos_em_destaque_sao_dinamicos(self):
        template = (
            RAIZ_PROJETO / 'app/templates/index.html'
        ).read_text(encoding='utf-8')

        self.assertIn('rankings_mercado.mais_negociadas[:5]', template)
        self.assertIn('Em destaque', template)
        self.assertIn('/mercado/altas', template)
        self.assertIn('/mercado/baixas', template)
        self.assertNotIn('/ativo/PETR4', template)
        self.assertNotIn('/ativo/VALE3', template)

    def test_menu_responsivo_expoe_controle_acessivel(self):
        parser = ElementosPorIdParser()
        parser.feed(
            (RAIZ_PROJETO / 'app/templates/index.html').read_text(encoding='utf-8')
        )

        tag, botao = parser.elementos['homeMenuToggle']
        _, menu = parser.elementos['homePrimaryNav']

        self.assertEqual(tag, 'button')
        self.assertEqual(botao['type'], 'button')
        self.assertEqual(botao['aria-controls'], 'homePrimaryNav')
        self.assertEqual(botao['aria-expanded'], 'false')
        self.assertEqual(menu['data-open'], 'false')

    def test_menu_responsivo_fecha_com_escape_e_atualiza_aria(self):
        javascript = (
            RAIZ_PROJETO / 'app/static/js/home.js'
        ).read_text(encoding='utf-8')

        self.assertIn('event.key === "Escape"', javascript)
        self.assertIn('setAttribute("aria-expanded"', javascript)
        self.assertIn('definirMenuAberto(false, true)', javascript)
        self.assertIn('window.matchMedia("(min-width: 861px)")', javascript)

    def test_template_identifica_noticias_externas_e_colunas_secundarias(self):
        template = (
            RAIZ_PROJETO / 'app/templates/index.html'
        ).read_text(encoding='utf-8')

        self.assertIn('(abre em uma nova aba)', template)
        self.assertIn('financial-table__mobile-secondary', template)
        self.assertIn('Atualize a página para tentar novamente.', template)

    def test_css_preserva_desktop_e_define_breakpoints_responsivos(self):
        css = (
            RAIZ_PROJETO / 'app/static/css/home.css'
        ).read_text(encoding='utf-8')

        self.assertIn('@media (max-width: 860px)', css)
        self.assertIn('.home-primary-nav[data-open="true"]', css)
        self.assertIn('@media (max-width: 680px)', css)
        self.assertIn('.financial-table__mobile-secondary', css)
        self.assertIn('grid-template-columns: repeat(2, minmax(0, 1fr))', css)


if __name__ == '__main__':
    unittest.main()
