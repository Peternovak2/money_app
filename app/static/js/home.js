const form = document.getElementById("formBusca");
const input = document.getElementById("tickerInput");

form.addEventListener("submit", function (event) {
  // Impede o formulário de recarregar a página
  event.preventDefault();

  // Pega o ticker digitado
  const ticker = input.value.trim().toUpperCase();

  // Se o usuário digitou alguma coisa
  if (!ticker) {
    return;
  }

  // Redireciona para a página do ativo
  window.location.href = `/ativo/${ticker}`;
});
