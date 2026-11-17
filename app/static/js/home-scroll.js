(() => {
  const seletor = ".home-body .home-content > .home-section:not(.home-dashboard)";
  const secoes = document.querySelectorAll(seletor);
  if (!secoes.length || !("IntersectionObserver" in window) || !window.matchMedia) return;
  const movimentoReduzido = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (movimentoReduzido.matches) return;
  const preparadas = new Set();
  const grupos = new Map();
  const temporizadores = new Map();
  let observador;
  function concluir(secao) {
    secao.classList.remove("home-scroll-pending", "home-scroll-entering");
    (grupos.get(secao) || []).forEach((item) => {
      item.classList.remove("home-scroll-child");
      item.style.removeProperty("--reveal-delay");
    });
    window.clearTimeout(temporizadores.get(secao));
    temporizadores.delete(secao);
    preparadas.delete(secao);
    grupos.delete(secao);
    observador?.unobserve(secao);
  }
  function revelar(secao) {
    if (!preparadas.has(secao) || !secao.classList.contains("home-scroll-pending")) return;
    observador.unobserve(secao);
    secao.classList.remove("home-scroll-pending");
    if (movimentoReduzido.matches || secao.matches(":focus-within, :target")) {
      concluir(secao);
      return;
    }
    secao.classList.add("home-scroll-entering");
    // Restaura mesmo sem animationend (aba suspensa ou CSS indisponivel).
    temporizadores.set(secao, window.setTimeout(() => concluir(secao), 1600));
  }
  try {
    observador = new IntersectionObserver((entradas) => {
      entradas.forEach(({ target, isIntersecting }) => {
        if (isIntersecting) revelar(target);
      });
    }, { threshold: 0, rootMargin: "0px 0px -24px 0px" });
    secoes.forEach((secao) => {
      // Nunca oculta conteudo inicial, foco ou destino de ancora.
      if (secao.getBoundingClientRect().top < window.innerHeight
          || secao.matches(":focus-within, :target") || secao.querySelector(":target")) return;
      preparadas.add(secao);
      const itens = Array.from(secao.querySelectorAll(
        ".market-panel, .featured-panel, .explore-card, .news-card, .markets-tabs, .markets-panel:not([hidden])"
      )).slice(0, 6);
      grupos.set(secao, itens);
      itens.forEach((item, indice) => {
        item.style.setProperty("--reveal-delay", `${(indice + 1) * 100}ms`);
        item.classList.add("home-scroll-child");
      });
      secao.classList.add("home-scroll-pending");
      observador.observe(secao);
    });
  } catch {
    Array.from(preparadas).forEach(concluir);
    observador?.disconnect();
    return;
  }
  document.addEventListener("animationend", (evento) => {
    if (evento.animationName === "home-section-enter"
        && !(grupos.get(evento.target) || []).length) concluir(evento.target);
  });
  document.addEventListener("focusin", (evento) => {
    const secao = evento.target.closest(".home-scroll-pending, .home-scroll-entering");
    if (secao) concluir(secao);
  });
  window.addEventListener("hashchange", () => {
    Array.from(preparadas).forEach((secao) => {
      if (secao.matches(":target") || secao.querySelector(":target")) concluir(secao);
    });
  });
  // Fallback do observer sem interceptar a rolagem nativa.
  const vigia = window.setInterval(() => {
    Array.from(preparadas).forEach((secao) => {
      const caixa = secao.getBoundingClientRect();
      if (caixa.top < window.innerHeight && caixa.bottom > 0) revelar(secao);
    });
    if (!preparadas.size) window.clearInterval(vigia);
  }, 2000);
  movimentoReduzido.addEventListener?.("change", (evento) => {
    if (!evento.matches) return;
    Array.from(preparadas).forEach(concluir);
    observador.disconnect();
    window.clearInterval(vigia);
  });
})();
