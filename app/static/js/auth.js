/**
 * auth.js
 * Validações client-side para o formulário de cadastro.
 * A validação definitiva sempre acontece no backend.
 */

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
