(() => {
  const indicador = document.getElementById("market-session-status");
  if (!indicador) return;
  const texto = indicador.querySelector("[data-session-label]");
  const rotulos = { aberto: "Aberto", fechado: "Fechado", indisponivel: "Status indisponível" };
  let controlador = null;
  let temporizador = null;
  let limite = null;
  let versao = 0;
  let ativo = true;

  function exibir(estado = "indisponivel", detalhe = "Não foi possível verificar a sessão regular de ações da B3.") {
    indicador.dataset.status = estado;
    texto.textContent = rotulos[estado];
    indicador.setAttribute("aria-label", `Sessão regular de ações da B3: ${rotulos[estado]}`);
    indicador.title = detalhe;
  }
  function parar() {
    versao += 1;
    window.clearTimeout(temporizador);
    window.clearTimeout(limite);
    controlador?.abort();
    controlador = null;
  }
  async function consultar() {
    parar();
    if (!ativo || document.hidden) return;
    const atual = versao;
    const ctrl = new AbortController();
    controlador = ctrl;
    let intervalo = 60000;
    limite = window.setTimeout(() => {
      if (versao === atual) { ctrl.abort(); exibir(); }
    }, 8000);
    try {
      const resposta = await fetch("/api/mercado/sessao", {
        signal: ctrl.signal, cache: "no-store", headers: { Accept: "application/json" },
      });
      if (!resposta.ok) throw new Error("Sessão indisponível");
      const dados = await resposta.json();
      if (atual !== versao || ctrl.signal.aborted || document.hidden) return;
      if (!Object.hasOwn(rotulos, dados.status) || dados.escopo !== "sessao_regular_acoes_b3"
        || !Number.isFinite(Date.parse(dados.referencia))) throw new Error("Resposta inválida");
      intervalo = Math.min(300000, Math.max(1000, (Number(dados.atualizar_em) || 60) * 1000));
      exibir(dados.status, typeof dados.detalhe === "string" ? dados.detalhe : "Sessão regular prevista pelo calendário da B3.");
    } catch {
      if (atual === versao) exibir();
    } finally {
      if (atual === versao) {
        window.clearTimeout(limite);
        controlador = null;
        if (ativo && !document.hidden) temporizador = window.setTimeout(consultar, intervalo);
      }
    }
  }
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { parar(); exibir(); }
    else consultar();
  });
  window.addEventListener("pagehide", () => { ativo = false; parar(); exibir(); });
  window.addEventListener("pageshow", evento => {
    if (evento.persisted) { ativo = true; consultar(); }
  });
  consultar();
})();
