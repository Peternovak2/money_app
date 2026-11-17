import unittest
from pathlib import Path


RAIZ_PROJETO = Path(__file__).resolve().parents[1]


class FrontendAuthTestCase(unittest.TestCase):
    def setUp(self):
        self.login = (RAIZ_PROJETO / "app/templates/login.html").read_text(
            encoding="utf-8"
        )
        self.cadastro = (RAIZ_PROJETO / "app/templates/cadastro.html").read_text(
            encoding="utf-8"
        )
        self.css = (RAIZ_PROJETO / "app/static/css/auth.css").read_text(
            encoding="utf-8"
        )
        self.javascript = (RAIZ_PROJETO / "app/static/js/auth.js").read_text(
            encoding="utf-8"
        )

    def test_cadastro_usa_grade_responsiva_sem_perder_campos(self):
        self.assertIn("auth-form--cadastro", self.cadastro)
        for campo in ("nome", "email", "senha", "confirmar_senha"):
            self.assertIn(f'id="{campo}"', self.cadastro)

        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", self.css)
        self.assertIn("@media (max-width: 700px)", self.css)
        self.assertIn("grid-template-columns: 1fr", self.css)

    def test_login_expoe_controle_acessivel_de_senha(self):
        self.assertIn("data-password-toggle", self.login)
        self.assertIn('aria-controls="senha"', self.login)
        self.assertIn('aria-pressed="false"', self.login)
        self.assertIn('type="button"', self.login)
        self.assertIn('/static/js/auth.js', self.login)

        self.assertIn('campoSenha.type === "password"', self.javascript)
        self.assertIn('deveExibir ? "text" : "password"', self.javascript)
        self.assertIn('setAttribute("aria-pressed", String(deveExibir))', self.javascript)

    def test_validacao_de_confirmacao_do_cadastro_foi_preservada(self):
        self.assertIn("formCadastro.addEventListener('submit'", self.javascript)
        self.assertIn("senha.value !== confirmarSenha.value", self.javascript)
        self.assertIn("event.preventDefault()", self.javascript)
        self.assertIn("confirmarSenha.focus()", self.javascript)
        self.assertIn('id="erroCadastro"', self.cadastro)
        self.assertIn('aria-live="polite"', self.cadastro)


if __name__ == "__main__":
    unittest.main()
