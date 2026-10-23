// Execute the complete result-page controller with an unavailable WebGL renderer.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import test from 'node:test';
const code = await readFile(new URL('../demo/results.js', import.meta.url), 'utf8');
const dataCode = await readFile(new URL('../demo/result-data.js', import.meta.url), 'utf8');
const example = JSON.parse(await readFile(new URL('../examples/frontend/material-room.json', import.meta.url), 'utf8'));
class Node {
  children = []; listeners = {}; dataset = {}; value = ''; ownText = '';
  constructor(tag = '') { this.tag = tag; }
  set textContent(value) { this.ownText = String(value); this.children = []; }
  get textContent() { return this.ownText + this.children.map(child => child.textContent).join('\n'); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.ownText = ''; this.children = children; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
}
async function controller() {
  const nodes = new Map();
  const querySelector = selector => { if (!nodes.has(selector)) nodes.set(selector, new Node()); return nodes.get(selector); };
  const context = vm.createContext({
    document: { querySelector, querySelectorAll: () => [], createElement: tag => new Node(tag) },
    Option: class extends Node { constructor(text, value) { super('option'); this.textContent = text; this.value = value; } },
    TextEncoder, AbortSignal,
  });
  const page = new vm.SourceTextModule(code, { context });
  const data = new vm.SourceTextModule(dataCode, { context });
  const renderer = new vm.SyntheticModule(['ResultView'], function () {
    this.setExport('ResultView', class { constructor() { throw new Error('WebGL unavailable'); } });
  }, { context });
  await page.link(specifier => specifier === './result-data.js' ? data : renderer);
  await page.evaluate();
  return {
    exports: page.namespace,
    get: selector => querySelector(selector),
    open: (text, name = 'input.json') => querySelector('#result-file').listeners.change({ target: { files: [{ size: new TextEncoder().encode(text).byteLength, name, text: async () => text }], value: name } }),
    defer: (promise, name) => querySelector('#result-file').listeners.change({ target: { files: [{ size: 1, name, text: () => promise }], value: name } }),
  };
}
test('full controller remains usable without WebGL and exposes actual evidence numerically', async () => {
  const page = await controller(); await page.open(JSON.stringify(example));
  assert.match(page.get('#render-status').textContent, /WebGL is unavailable/);
  assert.match(page.get('#result-status').textContent, /6 surfaces/);
  page.get('#result-surface').listeners.change({ target: { value: '0' } });
  assert.match(page.get('#surface-detail').textContent, /capture-00:echo:01/);
  assert.match(page.get('#surface-detail').textContent, /0\.01243 m/);
});
test('failed import leaves previous scene identity and selected evidence intact', async () => {
  const page = await controller(); await page.open(JSON.stringify(example), 'good.json');
  page.get('#result-surface').listeners.change({ target: { value: '0' } });
  const prior = page.get('#surface-detail').textContent;
  const bad = structuredClone(example); bad.dimensions = [null];
  await page.open(JSON.stringify(bad), 'bad.json');
  assert.match(page.get('#result-notice').textContent, /Previous result kept/);
  assert.match(page.get('#result-identity').textContent, /good.json/);
  assert.equal(page.get('#surface-detail').textContent, prior);
});
test('full controller safely displays deeply nested metadata without losing loaded result', async () => {
  const page = await controller(), value = structuredClone(example); value.example_metadata = null;
  const deep = '['.repeat(12000) + '0' + ']'.repeat(12000);
  const text = JSON.stringify(value).replace('"example_metadata":null', '"example_metadata":' + deep);
  await page.open(text, 'deep.json');
  assert.match(page.get('#result-notice').textContent, /Loaded deep.json/);
  assert.match(page.get('#result-identity').textContent, /too deeply nested/);
});
test('newer cancelled import wins over an older asynchronous file read', async () => {
  const page = await controller(); let finish;
  const pending = page.defer(new Promise(resolve => { finish = resolve; }), 'old.json');
  await page.open(JSON.stringify({ schema_version: '1.0', status: 'cancelled', surfaces: [], hypotheses: [], diagnostics: [], provenance: { physical_validation: false } }), 'new.json');
  finish(JSON.stringify(example)); await pending;
  assert.match(page.get('#result-status').textContent, /cancelled/);
  assert.match(page.get('#result-identity').textContent, /new.json/);
});

test('comparison subscribers observe only accepted snapshots and session freshness updates', async () => {
  const page = await controller(), seen = [];
  const unsubscribe = page.exports.subscribeBackendResult(value => seen.push(value));
  const input = structuredClone(example); input.session_revision = 3;
  await page.open(JSON.stringify(input));
  const accepted = page.exports.getBackendResult();
  assert.equal(seen.length, 1); assert.equal(seen[0], accepted);
  await page.open('[]'); assert.equal(seen.length, 1); assert.equal(page.exports.getBackendResult(), accepted);
  page.exports.markSessionRevision({ session_id: input.session_id, revision: 4 });
  assert.equal(seen.length, 2); assert.equal(seen[1].stale, true); assert.equal(accepted.stale, input.stale);
  unsubscribe(); page.exports.markSessionRevision({ session_id: input.session_id, revision: 3 }); assert.equal(seen.length, 2);
});
