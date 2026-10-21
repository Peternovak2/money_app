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


if __name__ == '__main__':
    unittest.main()
