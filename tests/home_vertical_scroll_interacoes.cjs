const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const fonte = fs.readFileSync('app/static/js/home-scroll.js', 'utf8');

// A rolagem pertence ao navegador, inclusive quando o reveal está habilitado.
for (const reduzido of [false, true]) {
  const listenersJanela = [];
  const listenersDocumento = [];
  const observadas = [];
  const secao = {
    classList: { remove() {}, add() {} },
    getBoundingClientRect: () => ({ top: 1000, bottom: 1300 }),
    matches: () => false, querySelector: () => null, querySelectorAll: () => [],
  };
  class Observer {
    constructor() {}
    observe(alvo) { observadas.push(alvo); }
  }
  vm.runInNewContext(fonte, {
    IntersectionObserver: Observer,
    document: {
      body: { classList: { contains: () => true } },
      querySelectorAll: () => [secao],
      addEventListener(nome) { listenersDocumento.push(nome); },
    },
    window: {
      IntersectionObserver: Observer,
      innerHeight: 800,
      setInterval() {}, clearInterval() {},
      matchMedia: () => ({ matches: reduzido, addEventListener() {} }),
      addEventListener(nome) { listenersJanela.push(nome); },
      scrollBy() { assert.fail('O reveal não deve mover a página.'); },
      scrollTo() { assert.fail('O reveal não deve reposicionar a página.'); },
    },
  });
  for (const evento of ['wheel', 'mousewheel', 'touchstart', 'touchmove', 'keydown', 'scroll']) {
    assert.ok(!listenersJanela.includes(evento), `Interceptação indevida: ${evento}`);
    assert.ok(!listenersDocumento.includes(evento), `Interceptação indevida: ${evento}`);
  }
  assert.equal(observadas.length, reduzido ? 0 : 1);
}
console.log('Rolagem nativa preservada: sem interceptação de mouse, touchpad, toque, teclado ou scroll.');
