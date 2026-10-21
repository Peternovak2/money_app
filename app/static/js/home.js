const form = document.getElementById("formBusca");
const input = document.getElementById("tickerInput");
const painel = document.getElementById("painelSugestoes");
const lista = document.getElementById("sugestoesAtivos");
const mensagem = document.getElementById("mensagemSugestoes");
const status = document.getElementById("buscaStatus");

const ATRASO_BUSCA_MS = 250;
const LIMITE_SUGESTOES = 8;

let temporizadorBusca = null;
let controladorBusca = null;
let sugestoes = [];
let indiceAtivo = -1;

function anunciar(texto) {
  status.textContent = texto;
}

function cancelarBusca() {
  window.clearTimeout(temporizadorBusca);
  temporizadorBusca = null;

  if (controladorBusca) {
    controladorBusca.abort();
    controladorBusca = null;
  }
}

function fecharPainel() {
  painel.hidden = true;
  input.setAttribute("aria-expanded", "false");
  input.removeAttribute("aria-activedescendant");
  indiceAtivo = -1;
}

function mostrarMensagem(estado, texto) {
  sugestoes = [];
  indiceAtivo = -1;
  lista.replaceChildren();
  lista.hidden = true;
  mensagem.textContent = texto;
  mensagem.hidden = false;
  painel.dataset.state = estado;
  painel.hidden = false;
  input.setAttribute("aria-expanded", "false");
  input.removeAttribute("aria-activedescendant");
  anunciar(texto);
}

function navegarParaAtivo(ticker) {
  cancelarBusca();
  fecharPainel();
  window.location.href = `/ativo/${encodeURIComponent(ticker)}`;
}

function definirOpcaoAtiva(novoIndice) {
  const opcoes = lista.querySelectorAll('[role="option"]');
  if (!opcoes.length) {
    return;
  }

  indiceAtivo = (novoIndice + opcoes.length) % opcoes.length;

  opcoes.forEach((opcao, indice) => {
    opcao.setAttribute("aria-selected", String(indice === indiceAtivo));
  });

  const opcaoAtiva = opcoes[indiceAtivo];
  input.setAttribute("aria-activedescendant", opcaoAtiva.id);
  opcaoAtiva.scrollIntoView({ block: "nearest" });
}

function criarOpcao(sugestao, indice) {
  const opcao = document.createElement("div");
  opcao.id = `sugestao-ativo-${indice}`;
  opcao.className = "home-search__option";
  opcao.setAttribute("role", "option");
  opcao.setAttribute("aria-selected", "false");

  const ticker = document.createElement("span");
  ticker.className = "home-search__option-ticker";
  ticker.textContent = sugestao.ticker;

  const nome = document.createElement("span");
  nome.className = "home-search__option-name";
  nome.textContent = sugestao.nome;

  opcao.append(ticker, nome);
  opcao.addEventListener("pointermove", () => definirOpcaoAtiva(indice));
  opcao.addEventListener("click", () => navegarParaAtivo(sugestao.ticker));
  return opcao;
}

function renderizarSugestoes(resultados) {
  sugestoes = resultados;
  indiceAtivo = -1;
  lista.replaceChildren();

  const fragmento = document.createDocumentFragment();
  sugestoes.forEach((sugestao, indice) => {
    fragmento.append(criarOpcao(sugestao, indice));
  });

  lista.append(fragmento);
  delete painel.dataset.state;
  mensagem.hidden = true;
  lista.hidden = false;
  painel.hidden = false;
  input.setAttribute("aria-expanded", "true");
  input.removeAttribute("aria-activedescendant");

  const quantidade = sugestoes.length;
  anunciar(`${quantidade} ${quantidade === 1 ? "sugestão encontrada" : "sugestões encontradas"}.`);
}

function sugestaoValida(item) {
  return (
    item &&
    typeof item.ticker === "string" &&
    typeof item.nome === "string"
  );
}

async function buscarSugestoes(consulta) {
  if (controladorBusca) {
    controladorBusca.abort();
  }

  const controladorAtual = new AbortController();
  controladorBusca = controladorAtual;
  mostrarMensagem("loading", "Buscando ativos…");

  const parametros = new URLSearchParams({
    q: consulta,
    limite: String(LIMITE_SUGESTOES),
  });

  try {
    const resposta = await fetch(`/api/ativos/sugestoes?${parametros}`, {
      headers: { Accept: "application/json" },
      signal: controladorAtual.signal,
    });

    if (!resposta.ok) {
      throw new Error(`Falha HTTP ${resposta.status}`);
    }

    const dados = await resposta.json();
    if (!Array.isArray(dados)) {
      throw new Error("Resposta de sugestões inválida");
    }

    if (controladorBusca !== controladorAtual || input.value.trim() !== consulta) {
      return;
    }

    const resultados = dados.filter(sugestaoValida);
    if (!resultados.length) {
      mostrarMensagem("empty", "Nenhum ativo encontrado.");
      return;
    }

    renderizarSugestoes(resultados);
  } catch (erro) {
    if (erro.name !== "AbortError" && controladorBusca === controladorAtual) {
      mostrarMensagem("error", "Não foi possível buscar ativos agora.");
    }
  } finally {
    if (controladorBusca === controladorAtual) {
      controladorBusca = null;
    }
  }
}

input.addEventListener("input", () => {
  cancelarBusca();
  fecharPainel();
  sugestoes = [];

  const consulta = input.value.trim();
  if (!consulta) {
    anunciar("");
    return;
  }

  temporizadorBusca = window.setTimeout(() => {
    buscarSugestoes(consulta);
  }, ATRASO_BUSCA_MS);
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    cancelarBusca();
    fecharPainel();
    sugestoes = [];
    anunciar("Sugestões fechadas.");
    return;
  }

  if (event.key === "Tab") {
    fecharPainel();
    return;
  }

  if (painel.hidden || !sugestoes.length) {
    return;
  }

  if (event.key === "ArrowDown") {
    event.preventDefault();
    definirOpcaoAtiva(indiceAtivo + 1);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    definirOpcaoAtiva(indiceAtivo - 1);
  } else if (event.key === "Enter" && indiceAtivo >= 0) {
    event.preventDefault();
    navegarParaAtivo(sugestoes[indiceAtivo].ticker);
  }
});

document.addEventListener("pointerdown", (event) => {
  if (!form.contains(event.target)) {
    fecharPainel();
  }
});

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const ticker = input.value.trim().toUpperCase();
  if (!ticker) {
    return;
  }

  navegarParaAtivo(ticker);
});
