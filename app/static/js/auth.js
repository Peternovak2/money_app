/**
 * auth.js
 * Validações client-side para o formulário de cadastro.
 * A validação definitiva sempre acontece no backend.
 */

const botoesExibirSenha = document.querySelectorAll("[data-password-toggle]");

botoesExibirSenha.forEach((botao) => {
  const campoId = botao.getAttribute("aria-controls");
  const campoSenha = document.getElementById(campoId);

  if (!campoSenha) {
    return;
  }

  botao.addEventListener("click", () => {
    const deveExibir = campoSenha.type === "password";
    campoSenha.type = deveExibir ? "text" : "password";
    botao.textContent = deveExibir ? "Ocultar" : "Mostrar";
    botao.setAttribute("aria-pressed", String(deveExibir));
  });
});

const formCadastro = document.getElementById('formCadastro');

if (formCadastro) {
  const senha = document.getElementById('senha');
  const confirmarSenha = document.getElementById('confirmar_senha');
  const erroCadastro = document.getElementById('erroCadastro');

  formCadastro.addEventListener('submit', function (event) {
    erroCadastro.textContent = '';
    confirmarSenha.classList.remove('campo-invalido');

    if (senha.value !== confirmarSenha.value) {
      event.preventDefault();
      erroCadastro.textContent = 'As senhas não coincidem.';
      confirmarSenha.classList.add('campo-invalido');
      confirmarSenha.focus();
    }
  });
}
