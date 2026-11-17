(() => {
  const mercados = document.querySelector("[data-markets]");
  if (!mercados) return;

  const abas = Array.from(mercados.querySelectorAll('[role="tab"]'));
  const paineis = Array.from(mercados.querySelectorAll('[role="tabpanel"]'));
  const filtros = Array.from(mercados.querySelectorAll("[data-region][aria-pressed]"));
  const resultado = mercados.querySelector("[data-market-result]");
  const mensagem = mercados.querySelector("[data-market-message]");
  const linkIndice = mercados.querySelector("[data-market-index-link]");

  function selecionarAba(aba) {
    abas.forEach((item) => {
      const ativa = item === aba;
      item.setAttribute("aria-selected", String(ativa));
      item.tabIndex = ativa ? 0 : -1;
    });
    paineis.forEach((painel) => {
      painel.hidden = painel.id !== aba.getAttribute("aria-controls");
    });
    mercados.dataset.category = aba.dataset.category;
  }

  function selecionarRegiao(filtro) {
    filtros.forEach((item) => {
      item.setAttribute("aria-pressed", String(item === filtro));
    });
    const disponivel = ["principais", "americas"].includes(filtro.dataset.region);
    resultado.dataset.region = filtro.dataset.region;
    resultado.dataset.state = disponivel ? "available" : "unavailable";
    mensagem.textContent = disponivel
      ? "Disponível: Ibovespa. Os demais índices ainda não possuem dados integrados."
      : `${filtro.textContent.trim()}: dados desta região ainda não disponíveis.`;
    linkIndice.hidden = !disponivel;
  }

  function navegarComTeclado(event, itens, atual, selecionar) {
    let indice = itens.indexOf(atual);
    if (event.key === "ArrowRight") indice = (indice + 1) % itens.length;
    else if (event.key === "ArrowLeft") indice = (indice - 1 + itens.length) % itens.length;
    else if (event.key === "Home") indice = 0;
    else if (event.key === "End") indice = itens.length - 1;
    else return;

    event.preventDefault();
    selecionar(itens[indice]);
    itens[indice].focus();
    itens[indice].scrollIntoView({ block: "nearest", inline: "nearest" });
  }

  abas.forEach((aba) => {
    aba.addEventListener("click", () => selecionarAba(aba));
    aba.addEventListener("keydown", (event) => navegarComTeclado(event, abas, aba, selecionarAba));
  });
  filtros.forEach((filtro) => {
    filtro.addEventListener("click", () => selecionarRegiao(filtro));
    filtro.addEventListener("keydown", (event) => navegarComTeclado(event, filtros, filtro, selecionarRegiao));
  });
})();
