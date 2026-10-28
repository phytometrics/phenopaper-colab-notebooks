export const REPOSITORY = 'https://github.com/phytometrics/phenopaper-colab-notebooks';
export const RAW = 'https://raw.githubusercontent.com/phytometrics/phenopaper-colab-notebooks/main';
export const SIZE_KEY = 'phenopaper.public-notebooks.size.v1';
export function displaySize(value) {
  if (value === null || value === '' || !['number', 'string'].includes(typeof value)) return 80;
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 && number <= 100 ? Math.round(number) : 80;
}
export function searchText(value) {
  return String(value ?? '').normalize('NFKD').replace(/\p{M}/gu, '').toLocaleLowerCase('en-US');
}
export function normalizeManifest(data) {
  if (data?.schema_version !== 1 || !Array.isArray(data.notebooks)) throw new Error('Unsupported notebook index.');
  const seen = new Set();
  return data.notebooks.flatMap(entry => {
    if (!entry || !/^p-[a-f0-9]{32}$/.test(entry.public_id) || seen.has(entry.public_id) || typeof entry.title !== 'string' || !['CPU', 'T4 GPU', 'CPU + T4 GPU'].includes(entry.compute) || !/^\d{4}-\d{2}-\d{2}$/.test(entry.validated_on)) return [];
    seen.add(entry.public_id);
    const item = {
      id: entry.public_id, title: entry.title, runtime: entry.compute, date: entry.validated_on,
      authors: Array.isArray(entry.authors) ? entry.authors.filter(value => typeof value === 'string') : [],
      journal: typeof entry.journal === 'string' ? entry.journal : '',
      scope: typeof entry.demonstration === 'string' ? entry.demonstration : '',
      tags: Array.isArray(entry.semantic_tags) ? entry.semantic_tags.filter(value => typeof value === 'string') : [],
      doi: typeof entry.doi === 'string' && /^10\.\d{4,9}\/\S+$/i.test(entry.doi) ? entry.doi : '',
      preview: entry.preview && typeof entry.preview.alt === 'string' ? `${RAW}/assets/previews/${entry.public_id}.png` : '',
      caption: typeof entry.preview?.caption === 'string' ? entry.preview.caption : '',
      colab: `https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/${entry.public_id}.ipynb`,
      github: `${REPOSITORY}/blob/main/notebooks/${entry.public_id}.ipynb`,
    };
    item.search = searchText([item.title, ...item.authors, item.journal, item.scope, ...item.tags, item.doi].join(' '));
    return [item];
  });
}
export function filterNotebooks(items, {query = '', runtime = '', tag = '', sort = 'newest'} = {}) {
  const terms = [...new Set(searchText(query).split(/[\s,]+/u).filter(Boolean))];
  return items.filter(item => (!runtime || item.runtime === runtime) && (!tag || item.tags.includes(tag)) && terms.every(term => item.search.includes(term)))
    .sort((a, b) => sort === 'title' ? a.title.localeCompare(b.title, 'en') : b.date.localeCompare(a.date) || a.title.localeCompare(b.title, 'en'));
}
