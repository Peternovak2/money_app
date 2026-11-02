import unittest
from pathlib import Path


RAIZ_PROJETO = Path(__file__).resolve().parents[1]


class FrontendHomeTestCase(unittest.TestCase):
    def test_bloco_informativo_inferior_foi_removido(self):
        template = (RAIZ_PROJETO / "app/templates/index.html").read_text(
            encoding="utf-8"
        )
        css = (RAIZ_PROJETO / "app/static/css/home.css").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("home-disclaimer", template)
        self.assertNotIn(".home-disclaimer", css)

    def test_atribuicao_das_noticias_continua_visivel(self):
        template = (RAIZ_PROJETO / "app/templates/index.html").read_text(
            encoding="utf-8"
        )

        self.assertIn("Agência Brasil", template)
        self.assertIn("noticia.fonte", template)

    def test_aviso_de_atraso_permanece_na_pagina(self):
        template = (RAIZ_PROJETO / "app/templates/ativo.html").read_text(
            encoding="utf-8"
        )

        self.assertIn("Dados de mercado sujeitos a atraso.", template)


if __name__ == "__main__":
    unittest.main()
