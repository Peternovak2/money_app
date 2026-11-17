const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const imagens = [false, true, true].map((complete, i) => ({ complete, naturalWidth: i === 2 ? 36 : 0,
  listeners: {}, addEventListener(nome, callback) { this.listeners[nome] = callback; }, remove() { this.removida = true; } }));
vm.runInNewContext(fs.readFileSync('app/static/js/asset-logos.js', 'utf8'), {
  document: { querySelectorAll: () => imagens },
});
assert.equal(imagens[1].removida, true); // Erro anterior à execução do script.
assert.ok(!imagens[2].removida); // Logo válido permanece.
imagens[0].listeners.error(); assert.equal(imagens[0].removida, true);
console.log('Logos: imagem válida, erro anterior e fallback posterior OK.');
