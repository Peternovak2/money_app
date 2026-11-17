(() => {
  if (!document.getElementById('analise-acompanhamento')) return;
  const numero = valor => new Intl.NumberFormat('pt-BR', {maximumFractionDigits: 4}).format(valor);
  const percentual = valor => `${valor > 0 ? '+' : ''}${numero(valor)}%`;
  const charts = new Map();
  function texto(tag, conteudo, classe) {
    const el = document.createElement(tag);
    el.textContent = conteudo;
    if (classe) el.className = classe;
    return el;
  }
  async function consultar(url, options = {}) {
    const resposta = await fetch(url, {...options, signal: AbortSignal.timeout(90000)});
    const dados = await resposta.json();
    if (!resposta.ok) throw Error(dados.detail || 'Dados indisponíveis');
    return dados;
  }
  function desenhar(id, serie, variacao, nome) {
    const el = document.getElementById(id);
    if (!el) return;
    charts.get(id)?.dispose();
    charts.delete(id);
    if (!window.echarts || !Array.isArray(serie) || serie.length < 2) {
      el.textContent = 'Histórico indisponível';
      return;
    }
    el.textContent = '';
    const chart = window.echarts.init(el);
    charts.set(id, chart);
    const cor = variacao >= 0 ? '#15956a' : '#dc4c64';
    chart.setOption({animation: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
      grid: {left: 10, right: 10, top: 16, bottom: 25},
      tooltip: {trigger: 'axis', renderMode: 'richText'},
      xAxis: {type: 'category', data: serie.map(p => p.data), axisLabel: {fontSize: 9}, boundaryGap: false},
      yAxis: {type: 'value', scale: true, show: false},
      series: [{name: nome, type: 'line', smooth: false, showSymbol: false,
        data: serie.map(p => p.valor), lineStyle: {color: cor, width: 2},
        areaStyle: {color: new window.echarts.graphic.LinearGradient(0, 0, 0, 1,
          [{offset: 0, color: cor + '35'}, {offset: 1, color: cor + '00'}])}}]});
    if ('ResizeObserver' in window) {
      const observer = new ResizeObserver(() => chart.isDisposed() ? observer.disconnect() : chart.resize());
      observer.observe(el);
    } else window.addEventListener('resize', () => { if (!chart.isDisposed()) chart.resize(); });
  }
  async function carregarMacro() {
    const cabecalho = document.getElementById('macro-usd');
    const lista = document.getElementById('macro-futures');
    try {
      const dados = await consultar('/api/paineis/macro');
      lista.replaceChildren();
      dados.sort((a,b) => ['BRL=X','CL=F','NG=F','GC=F','HG=F'].indexOf(a.id) - ['BRL=X','CL=F','NG=F','GC=F','HG=F'].indexOf(b.id));
      dados.forEach((item, i) => {
        const disponivel = item.estado === 'disponivel';
        const valor = disponivel ? `${numero(item.valor)} ${item.unidade} · ${percentual(item.variacao)} em 1M` : 'Indisponível';
        if (!i) {
          cabecalho.replaceChildren(texto('strong', 'USD para BRL'), texto('span', 'USD/BRL', 'macro-ticker'), texto('p', disponivel ? numero(item.valor) + ' BRL' : 'Indisponível', 'macro-price'), texto('p', disponivel ? percentual(item.variacao) + ' em 1M' : '', disponivel && item.variacao < 0 ? 'variation--negative' : 'variation--positive'),
            texto('small', disponivel ? `${item.inicio} a ${item.referencia} · Yahoo Finance` : 'Sem observações válidas'));
          desenhar('macro-mini-chart', item.serie, item.variacao, 'BRL por USD');
        } else {
          const li = texto('li', '', 'home-macro__row');
          li.append(texto('span', ({'CL=F':'◆','GC=F':'▲','NG=F':'♨','HG=F':'▦'})[item.id] || '●', 'macro-symbol'), texto('strong', item.nome), texto('small', `${item.id} · Futuro`),
            texto('span', disponivel ? numero(item.valor) + ' ' + item.unidade : 'Indisponível', 'macro-value'), texto('span', disponivel ? percentual(item.variacao) : '', disponivel ? (item.variacao >= 0 ? 'variation--positive' : 'variation--negative') : ''),
            texto('small', disponivel ? `${item.inicio} a ${item.referencia}` : 'Sem dados'));
          lista.append(li);
        }
      });
    } catch {
      cabecalho.textContent = 'Câmbio e futuros temporariamente indisponíveis';
    }
  }
  async function carregarSetores() {
    const lista = document.getElementById('sector-results');
    try {
      const dados = await consultar('/api/paineis/setores');
      dados.sort((a,b) => (b.variacao ?? -Infinity) - (a.variacao ?? -Infinity));
      const disponiveis = dados.filter(i => i.estado === 'disponivel');
      document.getElementById('desempenho-setor').dataset.sectorState = disponiveis.length ? 'available' : 'unavailable';
      const escala = Math.max(...disponiveis.map(i => Math.abs(i.variacao)), 1);
      lista.replaceChildren(texto('p', `Escala simétrica: −${numero(escala)}% a +${numero(escala)}%`, 'home-data-note'));
      function selecionar(item, botao) {
        lista.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b === botao)));

        document.getElementById('sector-detail').textContent = `${item.membros.length} ativos: ${item.membros.join(', ')} · ${item.inicio} a ${item.referencia} · Preços ajustados · ${item.fonte}`;
      }
      dados.forEach(item => {
        const botao = texto('button', '', 'sector-row');
        botao.type = 'button';
        botao.disabled = item.estado !== 'disponivel';
        botao.append(texto('span', item.nome), texto('strong', botao.disabled ? 'Indisponível' : percentual(item.variacao), item.variacao < 0 ? 'variation--negative' : 'variation--positive'));
        if (!botao.disabled) {
          botao.setAttribute('aria-pressed', 'false');
          const escalaEl = texto('span', '', 'sector-scale');
          const barra = texto('span', '', 'sector-bar');
          barra.style.width = `${Math.abs(item.variacao) / escala * 50}%`;
          barra.style.left = item.variacao >= 0 ? '50%' : `${50 - Math.abs(item.variacao) / escala * 50}%`;
          barra.style.background = item.variacao >= 0 ? '#15956a' : '#dc4c64';
          escalaEl.append(barra); botao.append(escalaEl);
          botao.addEventListener('click', () => selecionar(item, botao));
        }
        lista.append(botao);
        if (item === disponiveis[0]) selecionar(item, botao);
      });
      if (!disponiveis.length) document.getElementById('sector-detail').textContent = 'Nenhuma amostra tem cobertura suficiente neste momento.';
    } catch { lista.textContent = 'Dados setoriais temporariamente indisponíveis'; }
  }
  const form = document.getElementById('favorite-form');
  async function escrever(ticker, method) {
    const feedback = document.getElementById('favorite-feedback');
    try {
      await consultar(`/api/conta/favoritos/${encodeURIComponent(ticker)}`, {
        method, headers: {'X-CSRF-Token': form.dataset.csrf}});
      window.location.reload();
    } catch (erro) { feedback.textContent = erro.message; }
  }
  form?.addEventListener('submit', evento => {
    evento.preventDefault();
    const ticker = document.getElementById('favorite-ticker').value.trim().toUpperCase();
    if (!/^[A-Z0-9]{1,20}$/.test(ticker)) {
      document.getElementById('favorite-feedback').textContent = 'Informe um ticker válido.';
      return;
    }
    escrever(ticker, 'POST');
  });
  document.querySelectorAll('[data-remove-favorite]').forEach(botao => {
    botao.addEventListener('click', () => escrever(botao.dataset.removeFavorite, 'DELETE'));
  });
  const select = document.getElementById('watchlist-chart-select');
  let versaoHistorico = 0;
  async function carregarFavorito() {
    const versao = ++versaoHistorico;
    const status = document.getElementById('watchlist-chart-status');
    const ticker = select.value;
    status.textContent = 'Carregando histórico…';
    try {
      const dados = await consultar(`/api/${encodeURIComponent(ticker)}/historico?periodo=1mo`);
      if (versao !== versaoHistorico) return;
      if (dados.ticker !== ticker || dados.pontos.length < 2) throw Error('Histórico insuficiente');
      const serie = dados.pontos.map(p => ({data:p.time, valor:p.close}));
      desenhar('watchlist-mini-chart', serie, serie.at(-1).valor - serie[0].valor, ticker);
      status.textContent = `${ticker} · Yahoo Finance · preço em BRL · ${serie[0].data} a ${serie.at(-1).data}. Não é rentabilidade pessoal.`;
    } catch {
      if (versao !== versaoHistorico) return;
      desenhar('watchlist-mini-chart', [], 0, ticker);
      status.textContent = 'Histórico indisponível para este ativo.';
    }
  }
  select?.addEventListener('change', carregarFavorito);
  function iniciar() { carregarMacro(); carregarSetores(); if (select) carregarFavorito(); }
  if (document.readyState === 'complete') iniciar();
  else window.addEventListener('load', iniciar, {once:true});
})();
