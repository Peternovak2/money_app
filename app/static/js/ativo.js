const secaoGrafico = document.getElementById("grafico");

if (secaoGrafico) {
  const ticker = secaoGrafico.dataset.ticker;
  const periodoInicial = secaoGrafico.dataset.periodoInicial || "6mo";
  const conteudoGrafico = document.getElementById("grafico-conteudo");
  const canvasGrafico = document.getElementById("grafico-canvas");
  const statusGrafico = document.getElementById("grafico-status");
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
        color: ponto.close >= ponto.open ? "#22c55e" : "#ef4444",
      },
    }));

    return {
      animation: false,
      backgroundColor: "transparent",
      aria: { enabled: true },
      tooltip: {
        trigger: "axis",
        confine: true,
        axisPointer: { type: "line" },
        backgroundColor: "#111827",
        borderColor: "#334155",
        textStyle: { color: "#f8fafc" },
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
        label: { backgroundColor: "#334155" },
      },
      grid: [
        { left: 16, right: 64, top: 28, height: "55%" },
        { left: 16, right: 64, top: "70%", height: "12%" },
      ],
      xAxis: [
        {
          type: "category",
          data: datas,
          boundaryGap: true,
          axisLine: { lineStyle: { color: "#475569" } },
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
          axisLine: { lineStyle: { color: "#475569" } },
          axisTick: { show: false },
          axisLabel: {
            color: "#94a3b8",
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
            color: "#94a3b8",
            formatter(valor) {
              return formatadorPreco.format(valor);
            },
          },
          splitLine: { lineStyle: { color: "rgba(148, 163, 184, 0.14)" } },
        },
        {
          scale: true,
          gridIndex: 1,
          position: "right",
          splitNumber: 2,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: {
            color: "#94a3b8",
            formatter(valor) {
              return Intl.NumberFormat("pt-BR", {
                notation: "compact",
                maximumFractionDigits: 1,
              }).format(valor);
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
          borderColor: "#334155",
          backgroundColor: "#111827",
          fillerColor: "rgba(59, 130, 246, 0.18)",
          handleStyle: { color: "#64748b", borderColor: "#94a3b8" },
          moveHandleStyle: { color: "#64748b" },
          textStyle: { color: "#94a3b8" },
        },
      ],
      series: [
        {
          name: "Preço",
          type: "candlestick",
          data: candles,
          itemStyle: {
            color: "#22c55e",
            color0: "#ef4444",
            borderColor: "#22c55e",
            borderColor0: "#ef4444",
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
