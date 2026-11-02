import unittest
from html.parser import HTMLParser
from pathlib import Path


RAIZ_PROJETO = Path(__file__).resolve().parents[1]


class BotaoVoltarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.atributos = None

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag == "button" and "data-ativo-back" in atributos:
            self.atributos = atributos


class FrontendAtivoTestCase(unittest.TestCase):
    def test_template_expoe_botao_voltar_sem_breadcrumb(self):
        template = (RAIZ_PROJETO / "app/templates/ativo.html").read_text(
            encoding="utf-8"
        )
        parser = BotaoVoltarParser()
        parser.feed(template)

        self.assertIsNotNone(parser.atributos)
        self.assertEqual(parser.atributos["type"], "button")
        self.assertNotIn("ativo-breadcrumb", template)

    def test_voltar_usa_historico_interno_e_fallback_seguro(self):
        javascript = (RAIZ_PROJETO / "app/static/js/ativo.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("document.referrer", javascript)
        self.assertIn("paginaAnterior.origin === window.location.origin", javascript)
        self.assertIn("window.history.length > 1", javascript)
        self.assertIn("window.history.back()", javascript)
        self.assertIn('window.location.assign("/")', javascript)
        self.assertNotIn("window.location.assign(document.referrer)", javascript)

    def test_interacoes_existentes_permanecem_no_script(self):
        javascript = (RAIZ_PROJETO / "app/static/js/ativo.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("botao-acompanhar", javascript)
        self.assertIn("carregarHistorico", javascript)


if __name__ == "__main__":
    unittest.main()
