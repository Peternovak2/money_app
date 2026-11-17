const botaoVoltarAtivo = document.querySelector("[data-ativo-back]");

if (botaoVoltarAtivo) {
  botaoVoltarAtivo.addEventListener("click", () => {
    let origemAnteriorInterna = false;

    if (document.referrer) {
      try {
        const paginaAnterior = new URL(document.referrer);
        origemAnteriorInterna = paginaAnterior.origin === window.location.origin;
      } catch {
        origemAnteriorInterna = false;
      }
    }

    if (origemAnteriorInterna && window.history.length > 1) {
      window.history.back();
      return;
    }

    window.location.assign("/");
  });
}

const botaoAcompanhar = document.getElementById("botao-acompanhar");

if (botaoAcompanhar) {
  const tickerAcompanhado = botaoAcompanhar.dataset.ticker;
  const chaveAcompanhamento = `money-app:acompanhar:${tickerAcompanhado}`;
  const iconeAcompanhar = botaoAcompanhar.querySelector(
    ".botao-acompanhar__icone",
  );
  const textoAcompanhar = botaoAcompanhar.querySelector(
    ".botao-acompanhar__texto",
  );

  function atualizarBotaoAcompanhar(estaAcompanhando) {
    botaoAcompanhar.setAttribute("aria-pressed", String(estaAcompanhando));
    iconeAcompanhar.textContent = estaAcompanhando ? "★" : "☆";
    textoAcompanhar.textContent = estaAcompanhando
      ? "Acompanhando"
      : "Acompanhar";
  }

  try {
    atualizarBotaoAcompanhar(localStorage.getItem(chaveAcompanhamento) === "1");
  } catch {
    atualizarBotaoAcompanhar(false);
  }

  botaoAcompanhar.addEventListener("click", () => {
    const estaAcompanhando = botaoAcompanhar.getAttribute("aria-pressed") === "true";
    const proximoEstado = !estaAcompanhando;

    try {
      if (proximoEstado) {
        localStorage.setItem(chaveAcompanhamento, "1");
      } else {
        localStorage.removeItem(chaveAcompanhamento);
      }
    } catch {
      return;
    }

    atualizarBotaoAcompanhar(proximoEstado);
  });
}

const secaoGrafico = document.getElementById("grafico");

if (secaoGrafico) {
  const ticker = secaoGrafico.dataset.ticker;
  const periodoInicial = secaoGrafico.dataset.periodoInicial || "6mo";
  const conteudoGrafico = document.getElementById("grafico-conteudo");
  const canvasGrafico = document.getElementById("grafico-canvas");
  const statusGrafico = document.getElementById("grafico-status");
  const desempenhoPeriodo = document.getElementById("desempenho-periodo");
  const desempenhoVariacao = document.getElementById("desempenho-variacao");
  const desempenhoMaxima = document.getElementById("desempenho-maxima");
  const desempenhoMinima = document.getElementById("desempenho-minima");
  const desempenhoVolume = document.getElementById("desempenho-volume");
  const botoesPeriodo = Array.from(
    secaoGrafico.querySelectorAll("[data-periodo]"),
  );

  const formatadorPreco = new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const formatadorVolume = new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: 0,
  });
  const formatadorVolumeCompacto = new Intl.NumberFormat("pt-BR", {
    notation: "compact",
    maximumFractionDigits: 1,
  });
  const rotulosPeriodo = {
    "1mo": "1 mês",
    "3mo": "3 meses",
    "6mo": "6 meses",
    "1y": "1 ano",
    "5y": "5 anos",
    max: "Máximo",
  };

  let periodoCarregado = null;
  let periodoEmCarregamento = null;
  let controladorRequisicao = null;
  let grafico = null;

  function formatarData(data) {
    const [ano, mes, dia] = data.split("-");
    return `${dia}/${mes}/${ano}`;
  }

  function formatarDataEixo(data, periodo) {
    const [ano, mes, dia] = data.split("-");

    if (periodo === "max") {
      return ano;
    }

    if (periodo === "5y") {
      return `${mes}/${ano}`;
    }

    return `${dia}/${mes}`;
  }

  function atualizarPeriodoAtivo(periodo) {
    botoesPeriodo.forEach((botao) => {
      const estaAtivo = botao.dataset.periodo === periodo;
      botao.classList.toggle("grafico-periodo--ativo", estaAtivo);
      botao.setAttribute("aria-pressed", String(estaAtivo));
    });
  }

  function atualizarEstado(estado, mensagem = "") {
    const carregando = estado === "carregando";
    const sucesso = estado === "sucesso";

    conteudoGrafico.dataset.estado = estado;
    conteudoGrafico.setAttribute("aria-busy", String(carregando));
    canvasGrafico.hidden = !sucesso;
    statusGrafico.hidden = sucesso;
    statusGrafico.textContent = mensagem;
  }

  function atualizarDesempenho(pontos, periodo) {
    desempenhoPeriodo.textContent = rotulosPeriodo[periodo] || periodo;
    desempenhoVariacao.textContent = "—";
    desempenhoMaxima.textContent = "—";
    desempenhoMinima.textContent = "—";
    desempenhoVolume.textContent = "—";
    desempenhoVariacao.classList.remove(
      "desempenho-valor--positivo",
      "desempenho-valor--negativo",
    );

    if (!pontos.length) {
      return;
    }

    const primeiroFechamento = pontos[0].close;
    const ultimoFechamento = pontos[pontos.length - 1].close;
    const maxima = Math.max(...pontos.map((ponto) => ponto.high));
    const minima = Math.min(...pontos.map((ponto) => ponto.low));
    const volumesValidos = pontos
      .map((ponto) => ponto.volume)
      .filter((volume) => Number.isFinite(volume));

    if (primeiroFechamento !== 0) {
      const variacao = ((ultimoFechamento / primeiroFechamento) - 1) * 100;
      const sinal = variacao > 0 ? "+" : "";
      desempenhoVariacao.textContent = `${sinal}${formatadorPreco.format(variacao)}%`;

      if (variacao > 0) {
        desempenhoVariacao.classList.add("desempenho-valor--positivo");
      } else if (variacao < 0) {
        desempenhoVariacao.classList.add("desempenho-valor--negativo");
      }
    }

    desempenhoMaxima.textContent = formatadorPreco.format(maxima);
    desempenhoMinima.textContent = formatadorPreco.format(minima);

    if (volumesValidos.length) {
      const volumeMedio = volumesValidos.reduce(
        (total, volume) => total + volume,
        0,
      ) / volumesValidos.length;
      desempenhoVolume.textContent = formatadorVolumeCompacto.format(volumeMedio);
    }
  }

  function criarOpcoes(pontos, periodo) {
    const datas = pontos.map((ponto) => ponto.time);
    const candles = pontos.map((ponto) => [
      ponto.open,
      ponto.close,
      ponto.low,
      ponto.high,
    ]);
    const volumes = pontos.map((ponto) => ({
      value: ponto.volume,
      itemStyle: {
        color: ponto.close >= ponto.open ? "#07875c" : "#c93636",
      },
    }));

    return {
      animation: false,
      backgroundColor: "transparent",
      textStyle: {
        fontFamily: getComputedStyle(document.body).fontFamily,
        fontSize: 12,
      },
      aria: { enabled: true },
      tooltip: {
        trigger: "axis",
        confine: true,
        axisPointer: { type: "line" },
        backgroundColor: "#111827",
        borderColor: "#1d2939",
        textStyle: { color: "#f8fafc" },
        extraCssText: "box-shadow: 0 12px 28px rgba(16, 24, 40, 0.22); border-radius: 8px;",
        formatter(parametros) {
          const indice = parametros[0]?.dataIndex;
          const ponto = pontos[indice];

          if (!ponto) {
            return "";
          }

          const volume = ponto.volume === null
            ? "—"
            : formatadorVolume.format(ponto.volume);

          return [
            `<strong>${formatarData(ponto.time)}</strong>`,
            `Abertura: ${formatadorPreco.format(ponto.open)}`,
            `Máxima: ${formatadorPreco.format(ponto.high)}`,
            `Mínima: ${formatadorPreco.format(ponto.low)}`,
            `Fechamento: ${formatadorPreco.format(ponto.close)}`,
            `Volume: ${volume}`,
          ].join("<br>");
        },
      },
      axisPointer: {
        link: [{ xAxisIndex: [0, 1] }],
        label: { backgroundColor: "#344054" },
        lineStyle: { color: "#98a2b3", type: "dashed" },
      },
      grid: [
        { left: 18, right: 68, top: 28, height: "58%" },
        { left: 18, right: 68, top: "73%", height: "11%" },
      ],
      xAxis: [
        {
          type: "category",
          data: datas,
          boundaryGap: true,
          axisLine: { lineStyle: { color: "#e4e7ec" } },
          axisTick: { show: false },
          axisLabel: { show: false },
          splitLine: { show: false },
          min: "dataMin",
          max: "dataMax",
        },
        {
          type: "category",
          gridIndex: 1,
          data: datas,
          boundaryGap: true,
          axisLine: { lineStyle: { color: "#e4e7ec" } },
          axisTick: { show: false },
          axisLabel: {
            color: "#667085",
            hideOverlap: true,
            formatter(data) {
              return formatarDataEixo(data, periodo);
            },
          },
          splitLine: { show: false },
          min: "dataMin",
          max: "dataMax",
        },
      ],
      yAxis: [
        {
          scale: true,
          position: "right",
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: {
            color: "#667085",
            formatter(valor) {
              return formatadorPreco.format(valor);
            },
          },
          splitLine: { lineStyle: { color: "rgba(16, 24, 40, 0.07)" } },
        },
        {
          scale: true,
          gridIndex: 1,
          position: "right",
          splitNumber: 2,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: {
            color: "#98a2b3",
            formatter(valor) {
              return formatadorVolumeCompacto.format(valor);
            },
          },
          splitLine: { show: false },
        },
      ],
      dataZoom: [
        {
          type: "inside",
          xAxisIndex: [0, 1],
          start: 0,
          end: 100,
        },
        {
          type: "slider",
          xAxisIndex: [0, 1],
          bottom: 8,
          height: 20,
          start: 0,
          end: 100,
          showDataShadow: false,
          borderColor: "#e4e7ec",
          backgroundColor: "#f8fafc",
          fillerColor: "rgba(37, 99, 235, 0.12)",
          handleStyle: { color: "#ffffff", borderColor: "#94a3b8" },
          moveHandleStyle: { color: "#98a2b3" },
          textStyle: { color: "#667085" },
        },
      ],
      series: [
        {
          name: "Preço",
          type: "candlestick",
          data: candles,
          itemStyle: {
            color: "#07875c",
            color0: "#c93636",
            borderColor: "#07875c",
            borderColor0: "#c93636",
          },
        },
        {
          name: "Volume",
          type: "bar",
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes,
          barMaxWidth: 10,
        },
      ],
    };
  }

  function renderizarGrafico(pontos, periodo) {
    if (!window.echarts) {
      throw new Error("Apache ECharts não foi carregado");
    }

    atualizarEstado("sucesso");

    if (!grafico) {
      grafico = window.echarts.init(canvasGrafico, null, {
        renderer: "canvas",
      });
    }

    grafico.setOption(criarOpcoes(pontos, periodo), true);
    atualizarDesempenho(pontos, periodo);
    requestAnimationFrame(() => grafico.resize());
  }

  async function carregarHistorico(periodo) {
    if (periodo === periodoCarregado || periodo === periodoEmCarregamento) {
      return;
    }

    if (!ticker) {
      atualizarEstado("erro", "Não foi possível identificar o ativo.");
      return;
    }

    controladorRequisicao?.abort();

    const controladorAtual = new AbortController();
    controladorRequisicao = controladorAtual;
    periodoCarregado = null;
    periodoEmCarregamento = periodo;

    atualizarPeriodoAtivo(periodo);
    atualizarEstado("carregando", "Carregando histórico...");
    atualizarDesempenho([], periodo);

    const parametros = new URLSearchParams({ periodo });
    const url = `/api/${encodeURIComponent(ticker)}/historico?${parametros}`;

    try {
      const resposta = await fetch(url, {
        headers: { Accept: "application/json" },
        signal: controladorAtual.signal,
      });

      if (!resposta.ok) {
        throw new Error(`Falha HTTP ${resposta.status}`);
      }

      const dados = await resposta.json();

      if (!Array.isArray(dados.pontos)) {
        throw new Error("Resposta histórica inválida");
      }

      if (controladorRequisicao !== controladorAtual) {
        return;
      }

      if (dados.pontos.length === 0) {
        periodoCarregado = periodo;
        atualizarEstado("vazio", "Nenhum dado histórico disponível.");
        return;
      }

      renderizarGrafico(dados.pontos, periodo);
      periodoCarregado = periodo;
    } catch (erro) {
      if (erro.name === "AbortError") {
        return;
      }

      if (controladorRequisicao === controladorAtual) {
        atualizarEstado(
          "erro",
          "Não foi possível carregar o histórico.",
        );
      }
    } finally {
      if (controladorRequisicao === controladorAtual) {
        controladorRequisicao = null;
        periodoEmCarregamento = null;
      }
    }
  }

  const redimensionarGrafico = () => {
    if (grafico && !canvasGrafico.hidden) {
      grafico.resize();
    }
  };

  document.fonts?.ready.then(redimensionarGrafico);

  if ("ResizeObserver" in window) {
    const observador = new ResizeObserver(redimensionarGrafico);
    observador.observe(conteudoGrafico);
  } else {
    window.addEventListener("resize", redimensionarGrafico);
  }

  botoesPeriodo.forEach((botao) => {
    botao.addEventListener("click", () => {
      carregarHistorico(botao.dataset.periodo);
    });
  });

  carregarHistorico(periodoInicial);
}
