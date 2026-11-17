const form = document.getElementById("formBusca");
const input = document.getElementById("tickerInput");
const painel = document.getElementById("painelSugestoes");
const lista = document.getElementById("sugestoesAtivos");
const mensagem = document.getElementById("mensagemSugestoes");
const status = document.getElementById("buscaStatus");
const botaoMenu = document.querySelector("[data-home-menu-toggle]");
const menuPrincipal = document.querySelector("[data-home-menu]");
const sidebarToggle = document.getElementById("sidebarToggle");

const ATRASO_BUSCA_MS = 250;
const LIMITE_SUGESTOES = 8;

let temporizadorBusca = null;
let controladorBusca = null;
let sugestoes = [];
let indiceAtivo = -1;

function definirMenuAberto(aberto, devolverFoco = false) {
  if (!botaoMenu || !menuPrincipal) {
    return;
  }

  menuPrincipal.dataset.open = String(aberto);
  botaoMenu.setAttribute("aria-expanded", String(aberto));
  botaoMenu.setAttribute(
    "aria-label",
    aberto ? "Fechar menu principal" : "Abrir menu principal",
  );

  if (devolverFoco) {
    botaoMenu.focus();
  }
}

if (botaoMenu && menuPrincipal) {
  botaoMenu.addEventListener("click", () => {
    const abrir = botaoMenu.getAttribute("aria-expanded") !== "true";
    definirMenuAberto(abrir);
    if (abrir) menuPrincipal.querySelector("a")?.focus();
  });

  menuPrincipal.addEventListener("click", (event) => {
    const link = event.target.closest("a");
    if (link && botaoMenu.getAttribute("aria-expanded") === "true") {
      definirMenuAberto(false, true);
      if (link.hash) {
        const destino = document.querySelector(link.hash);
        if (destino) {
          destino.setAttribute("tabindex", "-1");
          destino.focus({ preventScroll: true });
        }
      }
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && botaoMenu.getAttribute("aria-expanded") === "true") {
      definirMenuAberto(false, true);
    }
  });

  document.addEventListener("pointerdown", (event) => {
    if (
      botaoMenu.getAttribute("aria-expanded") === "true" &&
      !botaoMenu.contains(event.target) &&
      !menuPrincipal.contains(event.target)
    ) {
      definirMenuAberto(false, menuPrincipal.contains(document.activeElement));
    }
  });

  window.matchMedia("(min-width: 861px)").addEventListener("change", (event) => {
    const foco = document.activeElement;
    if (document.body.classList.contains("home-sidebar-disabled")) {
      definirMenuAberto(false, menuPrincipal.contains(foco));
      return;
    }
    if (event.matches) {
      definirMenuAberto(false);
      if (foco === botaoMenu) sidebarToggle?.focus();
    } else if (foco === sidebarToggle || menuPrincipal.contains(foco)) {
      definirMenuAberto(false, true);
    }
  });
}

// O estado altera a apresentação; os links continuam disponíveis.
if (sidebarToggle) {
  sidebarToggle.addEventListener("click", () => {
    const expandida = document.body.classList.toggle("sidebar-expanded");
    const rotulo = expandida ? "Recolher barra lateral" : "Expandir barra lateral";
    sidebarToggle.setAttribute("aria-pressed", String(expandida));
    sidebarToggle.setAttribute("aria-label", rotulo);
    sidebarToggle.title = rotulo;
  });
}

function atualizarSecaoAtiva() {
  menuPrincipal?.querySelectorAll("a").forEach((link) => {
    const ativo = link.hash ? link.hash === window.location.hash : !window.location.hash;
    link.classList.toggle("home-primary-nav__link--active", ativo);
    if (ativo) {
      link.setAttribute("aria-current", link.hash ? "location" : "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
}

window.addEventListener("hashchange", atualizarSecaoAtiva);
atualizarSecaoAtiva();

const categoriasBusca = Array.from(document.querySelectorAll("[data-search-category]"));
const fecharBusca = document.getElementById("fecharBusca");
const tituloBusca = document.getElementById("tituloBusca");
const cacheBusca = new Map();
let categoriaAtual = "todos";
let versaoBusca = 0;
let consultaRenderizada = null;
let categoriaRenderizada = null;

function anunciar(texto) {
  status.textContent = texto;
}

function cancelarBusca() {
  versaoBusca += 1;
  window.clearTimeout(temporizadorBusca);
  temporizadorBusca = null;
  controladorBusca?.abort();
  controladorBusca = null;
}

function limparSelecao() {
  indiceAtivo = -1;
  input.removeAttribute("aria-activedescendant");
  lista.querySelectorAll('[role="option"]').forEach(opcao => opcao.setAttribute("aria-selected", "false"));
}

function abrirPainel() {
  painel.hidden = false;
  input.setAttribute("aria-expanded", "true");
}

function fecharPainel() {
  cancelarBusca();
  painel.hidden = true;
  input.setAttribute("aria-expanded", "false");
  limparSelecao();
  sugestoes = [];
  consultaRenderizada = null;
  lista.replaceChildren();
}

function mostrarMensagem(estado, texto) {
  sugestoes = [];
  consultaRenderizada = null;
  limparSelecao();
  lista.replaceChildren();
  lista.hidden = true;
  mensagem.textContent = texto;
  mensagem.hidden = false;
  painel.dataset.state = estado;
  lista.setAttribute("aria-busy", String(estado === "loading"));
  abrirPainel();
  anunciar(texto);
}

function navegarParaAtivo(ticker) {
  if (!/^[A-Z0-9]{4,12}$/.test(ticker)) return;
  fecharPainel();
  window.location.href = `/ativo/${encodeURIComponent(ticker)}`;
}

function definirOpcaoAtiva(novoIndice) {
  const opcoes = lista.querySelectorAll('[role="option"]');
  if (!opcoes.length) return;
  indiceAtivo = (novoIndice + opcoes.length) % opcoes.length;
  opcoes.forEach((opcao, indice) => opcao.setAttribute("aria-selected", String(indice === indiceAtivo)));
  const opcaoAtiva = opcoes[indiceAtivo];
  input.setAttribute("aria-activedescendant", opcaoAtiva.id);
  opcaoAtiva.scrollIntoView({ block: "nearest", inline: "nearest" });
}

function logoPermitido(valor) {
  if (typeof valor !== "string" || /\s/.test(valor)) return null;
  try {
    const url = new URL(valor);
    return url.origin === "https://icons.brapi.dev" && !url.username && !url.password
      && !url.search && !url.hash ? url.href : null;
  } catch {
    return null;
  }
}

function criarOpcao(sugestao, indice) {
  const opcao = document.createElement("div");
  opcao.id = `sugestao-ativo-${indice}`;
  opcao.className = "home-search__option";
  opcao.setAttribute("role", "option");
  opcao.setAttribute("aria-selected", "false");
  const avatar = document.createElement("span");
  avatar.className = "home-search__avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = sugestao.ticker.slice(0, 2);
  const logo = logoPermitido(sugestao.logo_url);
  if (logo) {
    const imagem = document.createElement("img");
    imagem.width = 36;
    imagem.height = 36;
    imagem.alt = "";
    imagem.loading = "lazy";
    imagem.decoding = "async";
    imagem.referrerPolicy = "no-referrer";
    imagem.addEventListener("error", () => imagem.remove(), { once: true });
    imagem.src = logo;
    avatar.append(imagem);
  }
  const identidade = document.createElement("span");
  identidade.className = "home-search__identity";
  const ticker = document.createElement("span");
  ticker.className = "home-search__option-ticker";
  ticker.textContent = sugestao.ticker;
  const nome = document.createElement("span");
  nome.className = "home-search__option-name";
  nome.textContent = sugestao.nome;
  identidade.append(ticker, nome);
  const tipo = document.createElement("span");
  tipo.className = "home-search__type";
  tipo.textContent = sugestao.tipo === "acao" ? "Ação" : "";
  opcao.append(avatar, identidade, tipo);
  opcao.addEventListener("pointermove", () => definirOpcaoAtiva(indice));
  opcao.addEventListener("click", () => navegarParaAtivo(sugestao.ticker));
  return opcao;
}

function renderizarSugestoes(resultados, consulta) {
  sugestoes = resultados;
  limparSelecao();
  lista.replaceChildren();
  const fragmento = document.createDocumentFragment();
  sugestoes.forEach((sugestao, indice) => fragmento.append(criarOpcao(sugestao, indice)));
  lista.append(fragmento);
  painel.dataset.state = "results";
  mensagem.hidden = true;
  lista.hidden = false;
  lista.setAttribute("aria-busy", "false");
  consultaRenderizada = consulta;
  categoriaRenderizada = categoriaAtual;
  abrirPainel();
  anunciar(`${sugestoes.length} ativos encontrados. Use as setas para selecionar.`);
}

function sugestaoValida(item) {
  return item && typeof item.ticker === "string" && /^[A-Z0-9]{4,12}$/.test(item.ticker)
    && typeof item.nome === "string" && item.nome.trim();
}

function resolverEnvio(consulta) {
  const exata = sugestoes.find(item => item.ticker === consulta.toUpperCase());
  if (exata || sugestoes.length === 1) {
    navegarParaAtivo((exata || sugestoes[0]).ticker);
  } else if (sugestoes.length) {
    mensagem.hidden = false;
    mensagem.textContent = "Há mais de uma correspondência. Selecione um ativo na lista.";
    anunciar(mensagem.textContent);
  }
}

async function buscarSugestoes(consulta, enviar = false) {
  cancelarBusca();
  const versaoAtual = versaoBusca;
  const categoria = categoriaAtual;
  const chave = `${categoria}|${consulta.toUpperCase()}`;
  tituloBusca.textContent = consulta ? "Resultados da pesquisa" : "Descobrir ações · por volume";
  const aplicar = resultados => {
    if (versaoAtual !== versaoBusca || painel.hidden || input.value.trim() !== consulta) return;
    if (!resultados.length) mostrarMensagem("empty", "Nenhum ativo encontrado nesta categoria.");
    else {
      renderizarSugestoes(resultados, consulta);
      if (enviar && consulta) resolverEnvio(consulta);
    }
  };
  mostrarMensagem("loading", consulta ? "Buscando ativos…" : "Carregando ativos da B3…");
  const anterior = cacheBusca.get(chave);
  if (anterior && Date.now() - anterior.quando < 60000) {
    aplicar(anterior.resultados);
    return;
  }
  const controladorAtual = new AbortController();
  controladorBusca = controladorAtual;
  const parametros = new URLSearchParams({ limite: String(LIMITE_SUGESTOES), categoria });
  if (consulta) parametros.set("q", consulta);
  const endpoint = consulta ? "sugestoes" : "descoberta";
  try {
    const resposta = await fetch(`/api/ativos/${endpoint}?${parametros}`, {
      headers: { Accept: "application/json" }, signal: controladorAtual.signal,
    });
    if (!resposta.ok) throw new Error(`Falha HTTP ${resposta.status}`);
    const dados = await resposta.json();
    if (versaoAtual !== versaoBusca || controladorBusca !== controladorAtual) return;
    if (!Array.isArray(dados)) throw new Error("Resposta de sugestões inválida");
    const resultados = dados.filter(sugestaoValida);
    if (cacheBusca.size >= 50) cacheBusca.delete(cacheBusca.keys().next().value);
    cacheBusca.set(chave, { quando: Date.now(), resultados });
    aplicar(resultados);
  } catch (erro) {
    if (erro.name !== "AbortError" && versaoAtual === versaoBusca && !painel.hidden) {
      mostrarMensagem("error", "Não foi possível consultar os ativos. Clique na pesquisa para tentar novamente.");
    }
  } finally {
    if (controladorBusca === controladorAtual) controladorBusca = null;
  }
}

function abrirPesquisa() {
  if (!painel.hidden && painel.dataset.state !== "error") return;
  buscarSugestoes(input.value.trim());
}

function agendarBusca(event) {
  if (event?.isComposing) return;
  cancelarBusca();
  const consulta = input.value.trim();
  mostrarMensagem("loading", consulta ? "Buscando ativos…" : "Carregando ativos da B3…");
  temporizadorBusca = window.setTimeout(() => buscarSugestoes(consulta), ATRASO_BUSCA_MS);
}
input.addEventListener("focus", abrirPesquisa);
input.addEventListener("click", abrirPesquisa);
input.addEventListener("input", agendarBusca);
input.addEventListener("compositionend", agendarBusca);
input.addEventListener("keydown", (event) => {
  if (event.isComposing) return;
  if (event.key === "Escape") {
    fecharPainel();
    anunciar("Pesquisa fechada.");
    return;
  }
  if (event.key === "Tab") {
    limparSelecao();
    return;
  }
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    if (painel.hidden) abrirPesquisa();
    if (sugestoes.length) definirOpcaoAtiva(indiceAtivo < 0
      ? (event.key === "ArrowUp" ? sugestoes.length - 1 : 0)
      : indiceAtivo + (event.key === "ArrowUp" ? -1 : 1));
  } else if (event.key === "Enter" && !painel.hidden && indiceAtivo >= 0) {
    event.preventDefault();
    navegarParaAtivo(sugestoes[indiceAtivo].ticker);
  }
});
fecharBusca.addEventListener("click", () => {
  input.focus({ preventScroll: true });
  fecharPainel();
});
categoriasBusca.forEach(botao => botao.addEventListener("click", () => {
  categoriaAtual = botao.dataset.searchCategory;
  categoriasBusca.forEach(item => item.setAttribute("aria-pressed", String(item === botao)));
  buscarSugestoes(input.value.trim());
}));
document.addEventListener("pointerdown", (event) => {
  if (!form.contains(event.target)) fecharPainel();
});
window.addEventListener("blur", fecharPainel);
form.addEventListener("focusout", event => {
  // Um clique numa opção não focável pode gerar relatedTarget=null antes do click.
  if (event.relatedTarget && !form.contains(event.relatedTarget)) fecharPainel();
});
form.addEventListener("keydown", event => {
  if (event.key === "Escape" && event.target !== input) {
    input.focus({ preventScroll: true });
    fecharPainel();
    anunciar("Pesquisa fechada.");
  }
});

if (window.visualViewport) {
  const ajustarAlturaBusca = () => {
    const viewport = window.visualViewport;
    const disponivel = viewport.height + viewport.offsetTop - input.getBoundingClientRect().bottom - 16;
    form.style.setProperty("--search-panel-height", `${Math.max(120, disponivel)}px`);
  };
  window.visualViewport.addEventListener("resize", ajustarAlturaBusca);
  window.visualViewport.addEventListener("scroll", ajustarAlturaBusca);
  input.addEventListener("focus", ajustarAlturaBusca);
  ajustarAlturaBusca();
}
form.addEventListener("submit", (event) => {
  event.preventDefault();
  const consulta = input.value.trim();
  if (!consulta) return;
  if (!painel.hidden && consultaRenderizada === consulta && categoriaRenderizada === categoriaAtual) resolverEnvio(consulta);
  else buscarSugestoes(consulta, true);
});

/* =====================================================================
   Dashboard: gráfico dos índices via /api/{ticker}/historico
   ===================================================================== */

(function () {
  "use strict";

  document.querySelectorAll("[data-movement-logo]").forEach(imagem => {
    imagem.addEventListener("error", () => imagem.remove());
    if (imagem.complete && !imagem.naturalWidth) imagem.remove();
  });
  const cardsIndice = Array.from(document.querySelectorAll("[data-index-symbol]"));
  let indiceSelecionado = cardsIndice[0];
  if (!indiceSelecionado) return;
  const iconeIndice = document.getElementById("dashboard-index-icon");
  const monogramaIndice = document.getElementById("dashboard-index-monogram");
  const tituloIndice = document.getElementById("dashboard-titulo");
  const badgeTicker = document.querySelector(".dashboard-chart-card__exchange");
  const PERIODO_INICIAL = "6mo";

  const corpoDashboard = document.getElementById("dashboard-ibov-body");
  if (!corpoDashboard) {
    return; // Elemento ausente: sai silenciosamente
  }

  const canvasIbov = document.getElementById("dashboard-ibov-canvas");
  const statusIbov = document.getElementById("dashboard-ibov-status");
  const elPreco = document.getElementById("dashboard-ibov-price");
  const elVariacao = document.getElementById("dashboard-ibov-change");
  const elPeriodo = document.getElementById("dashboard-ibov-period-label");
  const elTimestamp = document.getElementById("dashboard-ibov-timestamp");
  const elIndiceContexto = document.getElementById("indice-ibov-contexto");
  const botoesPeriodo = Array.from(
    document.querySelectorAll("[data-ibov-periodo]"),
  );

  const formatadorPonto = new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const rotulosPeriodo = {
    "1mo": "1 mês",
    "3mo": "3 meses",
    "6mo": "6 meses",
    "1y": "1 ano",
    "5y": "5 anos",
  };

  let graficoIbov = null;
  let periodoAtual = null;
  let controlador = null;

  function formatarData(isoDate) {
    const [ano, mes, dia] = isoDate.split("-");
    return `${dia}/${mes}/${ano}`;
  }

  function formatarDataEixo(isoDate, periodo) {
    const [ano, mes, dia] = isoDate.split("-");
    if (periodo === "5y") return `${mes}/${ano}`;
    return `${dia}/${mes}`;
  }

  function definirEstado(estado, mensagem) {
    corpoDashboard.dataset.estado = estado;
    corpoDashboard.setAttribute("aria-busy", String(estado === "carregando"));
    if (statusIbov) statusIbov.textContent = mensagem || "";
  }

  function atualizarCard(card, pontos, periodo) {
    const ultimo = pontos.at(-1);
    const variacao = pontos.length > 1 && pontos[0].close !== 0
      ? (ultimo.close / pontos[0].close - 1) * 100 : null;
    card.querySelector("[data-index-value]").textContent = `${formatadorPonto.format(ultimo.close)} pontos`;
    const elemento = card.querySelector("[data-index-change]");
    elemento.className = "index-summary__change";
    elemento.textContent = variacao === null ? "—"
      : `${variacao >= 0 ? "+" : ""}${formatadorPonto.format(variacao)}%`;
    elemento.setAttribute("aria-label", variacao === null ? "Variação indisponível" : `${elemento.textContent} em ${rotulosPeriodo[periodo]}`);
    const direcao = card.querySelector("[data-index-direction]");
    if (direcao) {
      direcao.textContent = variacao === null || variacao === 0 ? "" : variacao > 0 ? "↗" : "↘";
      direcao.className = `index-summary__direction ${variacao >= 0 ? "variation--positive" : "variation--negative"}`;
    }
    card.setAttribute("aria-busy", "false");
    if (variacao !== null) elemento.classList.add(variacao >= 0 ? "variation--positive" : "variation--negative");
    card.title = `${card.dataset.indexName} · Fechamento em ${formatarData(ultimo.time)} · Variação em ${rotulosPeriodo[periodo]} · Yahoo Finance`;
  }

  function indicarEstadoIndice(card, mensagem, carregando = false) {
    card.querySelector("[data-index-value]").textContent = "—";
    const variacao = card.querySelector("[data-index-change]");
    variacao.textContent = mensagem;
    variacao.className = "index-summary__change";
    variacao.removeAttribute("aria-label");
    const direcao = card.querySelector("[data-index-direction]");
    if (direcao) direcao.textContent = "";
    card.title = `${card.dataset.indexName} · ${mensagem}`;
    card.setAttribute("aria-busy", String(carregando));
  }
  function validarPontos(dados, simbolo) {
    if (dados.ticker !== simbolo || !Array.isArray(dados.pontos)
      || dados.pontos.some(p => !Number.isFinite(p.close) || !/^\d{4}-\d{2}-\d{2}$/.test(p.time))) {
      throw new Error("Histórico inválido");
    }
    return dados.pontos;
  }
  function atualizarBotaoAtivo(periodo) {
    botoesPeriodo.forEach((btn) => {
      const ativo = btn.dataset.ibovPeriodo === periodo;
      btn.classList.toggle("dashboard-period-btn--active", ativo);
      btn.setAttribute("aria-pressed", String(ativo));
    });
  }

  function atualizarCotacao(pontos) {
    if (!pontos || !pontos.length) {
      return;
    }

    const primeiro = pontos[0].close;
    const ultimo = pontos[pontos.length - 1].close;
    const variacao = pontos.length > 1 && primeiro !== 0 ? ((ultimo / primeiro) - 1) * 100 : null;
    const positivo = variacao !== null && variacao >= 0;

    if (elPreco) {
      elPreco.textContent = formatadorPonto.format(ultimo);
    }

    if (elVariacao && variacao !== null) {
      const sinal = positivo ? "+" : "";
      elVariacao.textContent = `${sinal}${formatadorPonto.format(variacao)}%`;
      elVariacao.className = "dashboard-chart-card__change";
      elVariacao.classList.add(
        positivo
          ? "dashboard-chart-card__change--positive"
          : "dashboard-chart-card__change--negative",
      );
    }

    if (elTimestamp) {
      const ultimaData = formatarData(pontos[pontos.length - 1].time);
      elTimestamp.textContent = `Fechamento · ${ultimaData}`;
    }
    atualizarCard(indiceSelecionado, pontos, periodoAtual);
    if (elIndiceContexto) elIndiceContexto.textContent = `${indiceSelecionado.dataset.indexName}: fechamento em ${formatarData(pontos.at(-1).time)} · Variação em ${rotulosPeriodo[periodoAtual]} · Fonte: Yahoo Finance.`;
  }
  function criarOpcoesGrafico(pontos, periodo) {
    const positivo = pontos.length >= 2
      && pontos[pontos.length - 1].close >= pontos[0].close;
    const corLinha = positivo ? "#0f7654" : "#c73550";
    const corArea = positivo ? "rgba(15, 118, 84, 0.08)" : "rgba(199, 53, 80, 0.07)";

    const datas = pontos.map((p) => p.time);
    const fechamentos = pontos.map((p) => p.close);

    return {
      animation: false,
      backgroundColor: "transparent",
      textStyle: {
        fontFamily: getComputedStyle(document.body).fontFamily,
        fontSize: 12,
      },
      aria: { enabled: true },
      grid: {
        left: 12,
        right: 72,
        top: 20,
        bottom: 36,
      },
      tooltip: {
        trigger: "axis",
        confine: true,
        axisPointer: {
          type: "line",
          lineStyle: { color: "#94a3b8", type: "dashed" },
        },
        backgroundColor: "#111827",
        borderColor: "#1d2939",
        textStyle: { color: "#f8fafc", fontSize: 12 },
        extraCssText:
          "box-shadow: 0 12px 28px rgba(16, 24, 40, 0.22); border-radius: 8px; padding: 10px 14px;",
        formatter(params) {
          const p = params[0];
          if (!p) return "";
          const data = formatarData(p.axisValue);
          const valor = formatadorPonto.format(p.value);
          return `<strong style="display:block;margin-bottom:4px">${data}</strong>${indiceSelecionado.dataset.indexSymbol}: <strong>${valor} pontos</strong>`;
        },
      },
      xAxis: {
        type: "category",
        data: datas,
        boundaryGap: false,
        axisLine: { lineStyle: { color: "#e4e7ec" } },
        axisTick: { show: false },
        axisLabel: {
          color: "#667085",
          fontSize: 12,
          hideOverlap: true,
          formatter(val) {
            return formatarDataEixo(val, periodo);
          },
        },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        scale: true,
        position: "right",
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: "#667085",
          fontSize: 12,
          formatter(val) {
            // Ibovespa em pontos — sem prefixo R$
            return formatadorPonto.format(val);
          },
        },
        splitLine: {
          lineStyle: { color: "rgba(16, 24, 40, 0.07)" },
        },
      },
      series: [
        {
          name: indiceSelecionado.dataset.indexName,
          type: "line",
          data: fechamentos,
          smooth: false,
          symbol: "none",
          lineStyle: { color: corLinha, width: 2 },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: positivo ? "rgba(15, 118, 84, 0.18)" : "rgba(199, 53, 80, 0.14)" },
                { offset: 1, color: "rgba(255, 255, 255, 0)" },
              ],
            },
          },
          emphasis: { disabled: true },
        },
      ],
    };
  }

  function renderizarGrafico(pontos, periodo) {
    if (!window.echarts) {
      definirEstado("erro", "Biblioteca de gráficos não carregada.");
      return;
    }

    definirEstado("sucesso");

    if (!graficoIbov) {
      graficoIbov = window.echarts.init(canvasIbov, null, { renderer: "canvas" });
    }

    graficoIbov.setOption(criarOpcoesGrafico(pontos, periodo), true);
    requestAnimationFrame(() => graficoIbov.resize());
    atualizarCotacao(pontos);
  }

  async function carregarHistorico(periodo, card = indiceSelecionado) {
    if (periodo === periodoAtual && card === indiceSelecionado && corpoDashboard.dataset.estado === "sucesso") return;

    if (controlador) {
      controlador.abort();
    }

    const ctrl = new AbortController();
    controlador = ctrl;
    periodoAtual = periodo;
    indiceSelecionado = card;
    card.dataset.consultado = "true";
    indicarEstadoIndice(card, "Carregando…", true);
    const simbolo = card.dataset.indexSymbol;
    if (iconeIndice) iconeIndice.dataset.headerIndex = simbolo;
    cardsIndice.forEach(item => {
      item.setAttribute("aria-pressed", String(item === card));
      item.setAttribute("tabindex", item === card ? "0" : "-1");
    });
    tituloIndice.textContent = card.dataset.indexName;
    badgeTicker.textContent = card.dataset.indexTicker || simbolo.replace(/^\^/, "");
    if (monogramaIndice) monogramaIndice.textContent = badgeTicker.textContent;
    if (elPeriodo) {
      elPeriodo.textContent = rotulosPeriodo[periodo];
      elPeriodo.title = `Variação entre o primeiro e o último fechamento de ${rotulosPeriodo[periodo]}`;
    }
    canvasIbov.setAttribute("aria-label", `Gráfico histórico de ${card.dataset.indexName}`);
    graficoIbov?.clear();
    [elPreco, elVariacao, elTimestamp].forEach(el => { if (el) el.textContent = ""; });
    if (elPreco) elPreco.textContent = "—";
    if (elIndiceContexto) elIndiceContexto.textContent = `${card.dataset.indexName} · Fonte: Yahoo Finance`;

    atualizarBotaoAtivo(periodo);
    definirEstado("carregando", `Carregando histórico de ${card.dataset.indexName}…`);

    const params = new URLSearchParams({ periodo });
    const url = `/api/${encodeURIComponent(simbolo)}/historico?${params}`;

    try {
      const resposta = await fetch(url, {
        headers: { Accept: "application/json" },
        signal: ctrl.signal,
      });

      if (!resposta.ok) {
        throw new Error(`HTTP ${resposta.status}`);
      }

      const dados = await resposta.json();

      if (controlador !== ctrl) return; // Requisição substituída

      validarPontos(dados, simbolo);

      if (dados.pontos.length === 0) {
        indicarEstadoIndice(card, "Sem histórico neste período");
        definirEstado("vazio", "Nenhum dado histórico disponível para este período.");
        return;
      }

      renderizarGrafico(dados.pontos, periodo);
    } catch (erro) {
      if (erro.name === "AbortError") return;

      if (controlador === ctrl) {
        indicarEstadoIndice(card, "Histórico indisponível · clique para tentar");
        definirEstado("erro", `Histórico de ${card.dataset.indexName} indisponível. Selecione outro índice ou tente novamente.`);
      }
    } finally {
      if (controlador === ctrl) {
        controlador = null;
      }
    }
  }

  // Redimensiona o gráfico quando o container muda de tamanho (sidebar)
  function redimensionar() {
    if (graficoIbov && corpoDashboard.dataset.estado === "sucesso") {
      graficoIbov.resize();
    }
  }

  document.fonts?.ready.then(redimensionar);

  if ("ResizeObserver" in window) {
    new ResizeObserver(redimensionar).observe(corpoDashboard);
  } else {
    window.addEventListener("resize", redimensionar);
  }

  // Cliques nos botões de período
  botoesPeriodo.forEach((btn) => {
    btn.addEventListener("click", () => {
      const periodo = btn.dataset.ibovPeriodo;
      if (periodo) carregarHistorico(periodo);
    });
  });

  function registrarCardIndice(card) {
    card.addEventListener("click", () => carregarHistorico(periodoAtual || PERIODO_INICIAL, card));
  }
  cardsIndice.forEach(registrarCardIndice);

  const carrossel = document.getElementById("indices-carousel");
  const botoesCarrossel = Array.from(document.querySelectorAll("[data-indices-scroll]"));
  function atualizarNavegacao() {
    const limite = Math.max(0, carrossel.scrollWidth - carrossel.clientWidth);
    const posicao = Math.max(0, Math.min(carrossel.scrollLeft, limite));
    botoesCarrossel.forEach(btn => {
      const ocultar = Number(btn.dataset.indicesScroll) < 0
        ? posicao <= 2 : limite - posicao <= 2;
      // Não deixa o foco preso em um botão que acabou de desaparecer.
      if (ocultar && document.activeElement === btn) carrossel.focus({ preventScroll: true });
      btn.hidden = ocultar;
      btn.disabled = ocultar;
    });
  }
  botoesCarrossel.forEach(btn => btn.addEventListener("click", () => {
    const larguraCard = cardsIndice[0].offsetWidth || 220;
    const espaco = Number.parseFloat(getComputedStyle(carrossel).columnGap) || 12;
    const passo = Math.min(larguraCard + espaco, carrossel.clientWidth * .65);
    carrossel.scrollBy({ left: Number(btn.dataset.indicesScroll) * passo,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }));
  carrossel.addEventListener("keydown", evento => {
    if (evento.ctrlKey || evento.metaKey || evento.altKey
      || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(evento.key)) return;
    evento.preventDefault();
    const alvo = evento.target.closest?.("[data-index-symbol]") || evento.target;
    let indice = cardsIndice.indexOf(alvo);
    if (indice < 0) indice = cardsIndice.indexOf(indiceSelecionado);
    if (evento.key === "Home") indice = 0;
    else if (evento.key === "End") indice = cardsIndice.length - 1;
    else indice = (indice + (evento.key === "ArrowRight" ? 1 : -1) + cardsIndice.length) % cardsIndice.length;
    cardsIndice.forEach((card, posicao) => card.setAttribute("tabindex", posicao === indice ? "0" : "-1"));
    cardsIndice[indice].focus({ preventScroll: true });
    cardsIndice[indice].scrollIntoView({ block: "nearest", inline: "nearest",
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  });
  carrossel.addEventListener("scroll", atualizarNavegacao, { passive: true });
  window.addEventListener("resize", atualizarNavegacao);
  if ("ResizeObserver" in window) new ResizeObserver(atualizarNavegacao).observe(carrossel);
  document.fonts?.ready.then(atualizarNavegacao);
  atualizarNavegacao();
  // Catálogo manual no template; cards ativos e seleção são compartilhados
  // com o gráfico e com a navegação por teclado do carrossel.
  const botaoAdicionar = document.getElementById("indices-add-toggle");
  const painelIndices = document.getElementById("indices-add-panel");
  const buscaIndices = document.getElementById("indices-picker-search");
  const fecharIndices = document.getElementById("indices-picker-close");
  const vazioIndices = document.getElementById("indices-picker-empty");
  const statusIndices = document.getElementById("indices-picker-status");
  if (botaoAdicionar && painelIndices && buscaIndices && fecharIndices && vazioIndices && statusIndices) {
    const opcoesIndices = Array.from(painelIndices.querySelectorAll("[data-index-option]"));
    const normalizarBusca = valor => valor.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
    const chaveIndices = "money-app.indices.v1";
    function salvarIndices() {
      try { window.localStorage.setItem(chaveIndices, JSON.stringify(cardsIndice.map(c => c.dataset.indexSymbol))); }
      catch { statusIndices.textContent = "Preferencias nao puderam ser salvas neste navegador."; }
    }
    function filtrarIndices() {
      const termo = normalizarBusca(buscaIndices.value.trim());
      opcoesIndices.forEach(opcao => {
        const adicionado = cardsIndice.some(card => card.dataset.indexSymbol === opcao.dataset.indexOption);
        opcao.disabled = !opcao.dataset.indexOption || (adicionado && opcao.dataset.indexOption === "^BVSP");
        opcao.querySelector(".indices-picker__action").textContent = adicionado
          ? (opcao.dataset.indexOption === "^BVSP" ? "Já adicionado" : "Remover") : opcao.dataset.indexOption ? "Adicionar" : "Indisponível";
        opcao.hidden = !normalizarBusca(`${opcao.dataset.optionName} ${opcao.dataset.optionTicker} ${opcao.dataset.indexOption}`).includes(termo);
      });
      vazioIndices.hidden = opcoesIndices.some(opcao => !opcao.hidden);
    }
    function fecharPainelIndices(restaurarFoco = false) {
      painelIndices.hidden = true;
      botaoAdicionar.setAttribute("aria-expanded", "false");
      if (restaurarFoco) botaoAdicionar.focus();
    }
    botaoAdicionar.hidden = false;
    botaoAdicionar.addEventListener("click", () => {
      if (!painelIndices.hidden) return fecharPainelIndices(true);
      buscaIndices.value = "";
      filtrarIndices();
      painelIndices.hidden = false;
      botaoAdicionar.setAttribute("aria-expanded", "true");
      buscaIndices.focus();
    });
    fecharIndices.addEventListener("click", () => fecharPainelIndices(true));
    buscaIndices.addEventListener("input", filtrarIndices);
    function removerIndice(existente) {
      if (!existente || existente.dataset.indexSymbol === "^BVSP") return;
      cardsIndice.splice(cardsIndice.indexOf(existente), 1);
      existente.remove();
      if (indiceSelecionado === existente) carregarHistorico(periodoAtual || PERIODO_INICIAL, cardsIndice[0]);
      salvarIndices(); filtrarIndices(); atualizarNavegacao();
      fecharPainelIndices(true);
      statusIndices.textContent = "Indice removido.";
      existente.indiceWrapper?.remove();
    }
    function adicionarOpcao(opcao, restaurando = false) {
      if (opcao.disabled || !opcao.dataset.indexOption) return;
      const existente = cardsIndice.find(card => card.dataset.indexSymbol === opcao.dataset.indexOption);
      if (existente) {
        if (restaurando || existente.dataset.indexSymbol === "^BVSP") return;
        removerIndice(existente);
        return;
      }
      // Reaproveita a estrutura do card sem inserir HTML de dados externos.
      const card = cardsIndice[0].cloneNode(true);
      card.dataset.indexSymbol = opcao.dataset.indexOption;
      card.dataset.indexName = opcao.dataset.optionName;
      card.dataset.indexTicker = opcao.dataset.optionTicker;
      delete card.dataset.consultado;
      card.querySelector(".index-summary__badge").textContent = opcao.dataset.optionBadge;
      card.querySelector(".index-summary__ticker").textContent = opcao.dataset.optionTicker;
      card.querySelector(".sr-only").textContent = opcao.dataset.optionName;
      card.setAttribute("aria-pressed", "false");
      card.setAttribute("tabindex", "-1");
      indicarEstadoIndice(card, "Carregando…", true);
      cardsIndice.push(card);
      const wrapper = document.createElement("div");
      wrapper.className = "index-card-wrap";
      const remover = document.createElement("button");
      remover.type = "button";
      remover.className = "index-card-remove";
      remover.textContent = "×";
      remover.setAttribute("aria-label", `Remover ${card.dataset.indexTicker}`);
      remover.title = `Remover ${card.dataset.indexTicker}`;
      remover.addEventListener("click", evento => {
        evento.preventDefault();
        evento.stopPropagation();
        removerIndice(card);
      });
      wrapper.append(card, remover);
      card.indiceWrapper = wrapper;
      carrossel.append(wrapper);
      registrarCardIndice(card);
      filtrarIndices();
      fecharPainelIndices();
      if (restaurando) return;
      salvarIndices();
      carregarHistorico(periodoAtual || PERIODO_INICIAL, card);
      card.focus({ preventScroll: true });
      card.scrollIntoView({ block: "nearest", inline: "nearest",
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
      atualizarNavegacao();
      statusIndices.textContent = `${opcao.dataset.optionName} adicionado ao carrossel.`;
    }
    opcoesIndices.forEach(opcao => opcao.addEventListener("click", () => adicionarOpcao(opcao)));
    try {
      const salvos = JSON.parse(window.localStorage.getItem(chaveIndices) || "[]");
      if (Array.isArray(salvos)) {
        [...new Set(salvos)].forEach(simbolo => {
          const opcao = opcoesIndices.find(o => o.dataset.indexOption === simbolo && simbolo);
          if (opcao) adicionarOpcao(opcao, true);
        });
      }
    } catch { /* Armazenamento bloqueado ou invalido: conserva IBOV sem sobrescrever. */ }
    filtrarIndices();
    atualizarNavegacao();
    painelIndices.addEventListener("keydown", evento => {
      if (evento.key === "Escape") {
        evento.preventDefault();
        fecharPainelIndices(true);
        return;
      }
      if (!["ArrowDown", "ArrowUp"].includes(evento.key)) return;
      const opcoes = opcoesIndices.filter(opcao => !opcao.hidden && !opcao.disabled);
      if (!opcoes.length) return;
      evento.preventDefault();
      const atual = opcoes.indexOf(document.activeElement);
      const proximo = atual < 0 ? (evento.key === "ArrowDown" ? 0 : opcoes.length - 1)
        : (atual + (evento.key === "ArrowDown" ? 1 : -1) + opcoes.length) % opcoes.length;
      opcoes[proximo].focus();
    });
    document.addEventListener("click", evento => {
      if (!painelIndices.hidden && !painelIndices.contains(evento.target) && !botaoAdicionar.contains(evento.target)) fecharPainelIndices();
    });
    document.addEventListener("focusin", evento => {
      if (!painelIndices.hidden && !painelIndices.contains(evento.target) && evento.target !== botaoAdicionar) fecharPainelIndices();
    });
    botaoAdicionar.addEventListener("keydown", evento => {
      if (evento.key === "Escape" && !painelIndices.hidden) fecharPainelIndices(true);
    });
  }
  // Consultas independentes: um índice indisponível não bloqueia os demais.
  cardsIndice.slice(1).forEach(async card => {
    try {
      const resposta = await fetch(`/api/${encodeURIComponent(card.dataset.indexSymbol)}/historico?periodo=${PERIODO_INICIAL}`);
      if (!resposta.ok) throw new Error("Indisponível");
      const pontos = validarPontos(await resposta.json(), card.dataset.indexSymbol);
      if (!pontos.length) throw new Error("Sem histórico");
      if (!card.dataset.consultado) atualizarCard(card, pontos, PERIODO_INICIAL);
    } catch {
      if (!card.dataset.consultado) indicarEstadoIndice(card, "Histórico indisponível · clique para tentar");
    }
  });
  // ECharts usa defer: aguarda window.load para garantir que esta disponivel
  if (document.readyState === "complete") {
    carregarHistorico(PERIODO_INICIAL);
  } else {
    window.addEventListener("load", () => carregarHistorico(periodoAtual || PERIODO_INICIAL), { once: true });
  }
})();
