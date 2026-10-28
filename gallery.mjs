import {RAW, SIZE_KEY, displaySize, normalizeManifest, filterNotebooks} from './model.mjs';

const $ = id => document.getElementById(id);
const controls = ['query', 'runtime', 'tag', 'sort'];
let items = [];
let opener = null;
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function link(text, url, className) {
  const node = element('a', text, className);
  node.href = url;
  node.target = '_blank';
  node.rel = 'noopener noreferrer';
  return node;
}
function image(item) {
  const node = element('img');
  node.src = item.preview;
  node.alt = item.caption || item.title;
  node.loading = 'lazy';
  node.decoding = 'async';
  node.addEventListener('error', () => { node.replaceWith(element('span', 'Preview unavailable', 'missing')); }, {once: true});
  return node;
}
function badges(item) {
  const node = element('div', undefined, 'badges');
  node.append(element('span', item.runtime, 'runtime'), element('span', 'AI-verified · execution checks', 'verified'), element('span', `Checked ${item.date}`));
  return node;
}
function actions(item) {
  const node = element('div', undefined, 'actions');
  node.append(link('Open in Colab ↗', item.colab, 'primary'), link('GitHub ↗', item.github));
  if (item.doi) node.append(link('Paper DOI ↗', `https://doi.org/${encodeURI(item.doi).replace(/#/g, '%23').replace(/\?/g, '%3F')}`));
  return node;
}
function openDetail(item, button) {
  opener = button || document.activeElement;
  const container = $('detail-content');
  container.replaceChildren();
  const title = element('h2', item.title);
  title.id = 'detail-title';
  container.append(title, badges(item));
  if (item.preview) container.append(image(item));
  container.append(element('p', [item.journal, item.authors.join(' · ')].filter(Boolean).join(' — '), 'bibliography'), element('h3', 'Demonstration scope / 実行範囲'), element('p', item.scope || 'See the notebook for its execution scope.'), element('p', 'Execution checks do not guarantee scientific correctness or reproduction of the full paper.', 'limitation'), element('p', item.tags.join(' · '), 'tags'), actions(item));
  history.replaceState(null, '', `#${item.id}`);
  if (!$('detail').open) $('detail').showModal();
}
function render() {
  const found = filterNotebooks(items, Object.fromEntries(controls.map(id => [id, $(id).value])));
  const fragment = document.createDocumentFragment();
  for (const item of found) {
    const card = element('article', undefined, 'card');
    const preview = element('button', undefined, 'preview');
    preview.type = 'button';
    preview.setAttribute('aria-label', `${item.title} — details`);
    preview.title = `${item.title}\n${item.runtime} · Checked ${item.date}\n${item.scope}`;
    if (item.preview) preview.append(image(item));
    else preview.append(element('span', 'No preview', 'missing'));
    preview.append(element('span', item.title, 'preview-title'));
    preview.addEventListener('click', () => openDetail(item, preview));
    const body = element('div', undefined, 'card-body');
    const title = element('button', item.title, 'card-title');
    title.type = 'button';
    title.addEventListener('click', () => openDetail(item, title));
    body.append(title, badges(item), element('p', [item.journal, item.authors.join(' · ')].filter(Boolean).join(' — '), 'bibliography'), element('p', item.scope, 'scope'), element('p', item.tags.join(' · '), 'tags'), actions(item));
    card.append(preview, body);
    fragment.append(card);
  }
  $('gallery').replaceChildren(fragment);
  $('status').textContent = `${found.length} / ${items.length} notebooks`;
  $('empty').hidden = found.length !== 0;
}
function resize() {
  const size = displaySize($('size').value);
  document.documentElement.style.setProperty('--card-width', `${110 + size * 2.7}px`);
  document.documentElement.style.setProperty('--text-size', `${12 + size * .035}px`);
  document.documentElement.style.setProperty('--scope-lines', String(size >= 90 ? 7 : size >= 70 ? 4 : 2));
  $('gallery').classList.toggle('compact', size < 50);
  $('size-label').textContent = size < 50 ? 'Thumbnails · hover / tap for details' : size === 80 ? 'Default' : size > 80 ? 'Larger' : 'Smaller';
  try { localStorage.setItem(SIZE_KEY, String(size)); } catch { /* Storage is optional. */ }
}
async function load() {
  $('retry').hidden = true;
  $('status').textContent = 'Loading notebooks…';
  try {
    const response = await fetch(`${RAW}/publication.json`, {signal: AbortSignal.timeout(20000)});
    if (!response.ok) throw new Error(`GitHub returned ${response.status}`);
    items = normalizeManifest(await response.json());
    const tags = [...new Set(items.flatMap(item => item.tags))].sort();
    const selected = $('tag').value;
    $('tag').replaceChildren(new Option('All tags', ''), ...tags.map(tag => new Option(tag, tag)));
    if (tags.includes(selected)) $('tag').value = selected;
    render();
    const requested = items.find(item => `#${item.id}` === location.hash);
    if (requested) openDetail(requested);
  } catch {
    $('status').textContent = 'Could not load the GitHub notebook index. Please retry or browse the GitHub index above.';
    $('retry').hidden = false;
  }
}
for (const id of controls) $(id).addEventListener('input', render);
$('reset').addEventListener('click', () => { $('query').value = ''; $('runtime').value = ''; $('tag').value = ''; $('sort').value = 'newest'; render(); });
$('retry').addEventListener('click', load);
$('size').addEventListener('input', resize);
$('close').addEventListener('click', () => $('detail').close());
$('detail').addEventListener('click', event => { if (event.target === $('detail')) { const box = $('detail').getBoundingClientRect(); if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) $('detail').close(); } });
$('detail').addEventListener('close', () => { history.replaceState(null, '', location.pathname + location.search); opener?.focus(); });
try { $('size').value = String(displaySize(localStorage.getItem(SIZE_KEY))); } catch { /* Default size. */ }
resize();
void load();
