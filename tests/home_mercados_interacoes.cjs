// Executa o script de produção com elementos simulados; não valida renderização CSS.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const fixture = JSON.parse(fs.readFileSync(0, 'utf8'));
let foco;
class Elemento {
  constructor(id = '', dataset = {}, text = '') {
    Object.assign(this, { id, dataset, textContent: text, atributos: {}, eventos: {}, hidden: false });
  }
  setAttribute(nome, valor) { this.atributos[nome] = valor; }
  getAttribute(nome) { return this.atributos[nome]; }
  addEventListener(tipo, fn) { this.eventos[tipo] = fn; }
  focus() { foco = this; }
  scrollIntoView() {}
  disparar(tipo, key) {
    let prevenido = false;
    this.eventos[tipo]({ key, preventDefault() { prevenido = true; } });
    return prevenido;
  }
}
const abas = fixture.abas.map((item) => {
  const aba = new Elemento(item.id, { category: item.category });
  aba.setAttribute('aria-controls', item.controls);
  return aba;
});
const paineis = fixture.paineis.map((id) => new Elemento(id));
const filtros = fixture.filtros.map((item) => new Elemento('', { region: item.region }, item.text));
const resultado = new Elemento();
const mensagem = new Elemento();
const link = new Elemento();
const raiz = new Elemento();
raiz.querySelectorAll = (seletor) => ({
  '[role="tab"]': abas, '[role="tabpanel"]': paineis,
  '[data-region][aria-pressed]': filtros,
})[seletor];
raiz.querySelector = (seletor) => ({
  '[data-market-result]': resultado, '[data-market-message]': mensagem,
  '[data-market-index-link]': link,
})[seletor];
vm.runInNewContext(fs.readFileSync('app/static/js/home-mercados.js', 'utf8'), {
  document: { querySelector: () => raiz },
});
function conferirAba(aba) {
  assert.equal(raiz.dataset.category, aba.dataset.category);
  for (const item of abas) {
    assert.equal(item.getAttribute('aria-selected'), String(item === aba));
    assert.equal(item.tabIndex, item === aba ? 0 : -1);
  }
  assert.equal(paineis.filter((painel) => !painel.hidden).length, 1);
  assert.equal(paineis.find((painel) => !painel.hidden).id, aba.getAttribute('aria-controls'));
}
for (const aba of abas) { aba.disparar('click'); conferirAba(aba); }
assert(abas.at(-1).disparar('keydown', 'ArrowRight'));
conferirAba(abas[0]);
assert.equal(foco, abas[0]);
abas[0].disparar('keydown', 'ArrowLeft'); conferirAba(abas.at(-1));
abas.at(-1).disparar('keydown', 'Home'); conferirAba(abas[0]);
abas[0].disparar('keydown', 'End'); conferirAba(abas.at(-1));
assert.equal(abas.at(-1).disparar('keydown', 'Tab'), false);
for (const filtro of filtros) {
  filtro.disparar('click');
  assert.equal(resultado.dataset.region, filtro.dataset.region);
  assert.equal(filtros.filter((item) => item.getAttribute('aria-pressed') === 'true').length, 1);
  const disponivel = ['principais', 'americas'].includes(filtro.dataset.region);
  assert.equal(link.hidden, !disponivel);
  assert.equal(resultado.dataset.state, disponivel ? 'available' : 'unavailable');
  assert(mensagem.textContent.includes(disponivel ? 'Ibovespa' : 'dados desta'));
}
filtros.at(-1).disparar('keydown', 'ArrowRight');
assert.equal(foco, filtros[0]);
assert.equal(resultado.dataset.region, 'principais');
console.log('OK: clique, setas, Home/End, foco, ARIA, painéis e regiões indisponíveis.');
