import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

import { selectDueArticle, validateEntry, validateManifest } from './select-due-article.mjs'

const REPO = join(dirname(fileURLToPath(import.meta.url)), '..', '..')

const entry = (slug, date, extra = {}) => ({
  slug,
  branch: `blog/${slug}`,
  article: `src/content/blog/en/${slug}.md`,
  date,
  ...extra,
})

const nothingPublished = () => false

test('no publica nada cuando ninguna fecha ha vencido', () => {
  const r = selectDueArticle({
    entries: [entry('a', '2026-09-05')],
    today: '2026-09-01',
    alreadyPublishedToday: false,
    isPublished: nothingPublished,
  })
  assert.equal(r.action, 'none')
})

test('publica el articulo cuya fecha es hoy', () => {
  const r = selectDueArticle({
    entries: [entry('a', '2026-09-01')],
    today: '2026-09-01',
    alreadyPublishedToday: false,
    isPublished: nothingPublished,
  })
  assert.equal(r.action, 'publish')
  assert.equal(r.entry.slug, 'a')
})

// Este es el fallo de 2026-08-30: la cola de GitHub no sirvio ninguna de las
// cuatro salidas del dia y el articulo se quedo sin publicar, sin reintento.
test('recupera un articulo cuya fecha ya paso (el cron se salto ese dia)', () => {
  const r = selectDueArticle({
    entries: [entry('atrasado', '2026-08-30')],
    today: '2026-09-03',
    alreadyPublishedToday: false,
    isPublished: nothingPublished,
  })
  assert.equal(r.action, 'publish')
  assert.equal(r.entry.slug, 'atrasado')
})

test('con varios vencidos publica el mas antiguo y deja el resto en cola', () => {
  const r = selectDueArticle({
    entries: [entry('nuevo', '2026-09-02'), entry('viejo', '2026-08-30')],
    today: '2026-09-03',
    alreadyPublishedToday: false,
    isPublished: nothingPublished,
  })
  assert.equal(r.entry.slug, 'viejo')
  assert.equal(r.backlog, 1)
})

// La regla de un articulo al dia: dos merges el mismo dia sacan dos posts de
// LinkedIn a la vez, que es lo que las fechas alternas existen para evitar.
test('no publica un segundo articulo el mismo dia', () => {
  const r = selectDueArticle({
    entries: [entry('a', '2026-08-30'), entry('b', '2026-08-31')],
    today: '2026-09-03',
    alreadyPublishedToday: true,
    isPublished: nothingPublished,
  })
  assert.equal(r.action, 'none')
})

test('salta los que ya estan en main y coge el siguiente', () => {
  const r = selectDueArticle({
    entries: [entry('ya-publicado', '2026-08-30'), entry('pendiente', '2026-08-31')],
    today: '2026-09-03',
    alreadyPublishedToday: false,
    isPublished: (e) => e.slug === 'ya-publicado',
  })
  assert.equal(r.entry.slug, 'pendiente')
})

test('es idempotente: si todo lo vencido esta en main, no hace nada', () => {
  const r = selectDueArticle({
    entries: [entry('a', '2026-08-30')],
    today: '2026-09-03',
    alreadyPublishedToday: false,
    isPublished: () => true,
  })
  assert.equal(r.action, 'none')
})

test('el orden del manifiesto no altera la eleccion', () => {
  const a = entry('a', '2026-09-01')
  const b = entry('b', '2026-09-02')
  const opts = { today: '2026-09-05', alreadyPublishedToday: false, isPublished: nothingPublished }
  assert.equal(selectDueArticle({ entries: [a, b], ...opts }).entry.slug, 'a')
  assert.equal(selectDueArticle({ entries: [b, a], ...opts }).entry.slug, 'a')
})

test('validateEntry exige los campos obligatorios', () => {
  assert.equal(validateEntry(entry('a', '2026-09-01'), 0).length, 0)
  assert.match(validateEntry({ slug: 'a', branch: 'b', date: '2026-09-01' }, 0)[0], /article/)
  assert.match(validateEntry(entry('a', '01-09-2026'), 0)[0], /YYYY-MM-DD/)
  assert.match(validateEntry(entry('a', '2026-09-01', { blockIfMatches: '[' }), 0)[0], /regexp/)
})

test('validateManifest caza slugs duplicados', () => {
  const errs = validateManifest({ articles: [entry('a', '2026-09-01'), entry('a', '2026-09-02')] })
  assert.equal(errs.length, 1)
  assert.match(errs[0], /duplicado/)
})

// El manifiesto real tiene que estar bien formado, no solo los ejemplos.
test('el manifiesto del repo es valido', () => {
  const manifest = JSON.parse(readFileSync(join(REPO, '.github/publish-schedule.json'), 'utf-8'))
  assert.deepEqual(validateManifest(manifest), [])
  // An empty queue is valid after the last scheduled article is published.
})

// Una fecha libre tiene que estarlo en los dos calendarios. Esto ya se colo una
// vez a mano (08-24, ver docs/blog-publishing.md); aqui deja de depender de que
// alguien se acuerde de mirar.
test('ninguna fecha del manifiesto choca con schedule.json de LinkedIn', () => {
  const manifest = JSON.parse(readFileSync(join(REPO, '.github/publish-schedule.json'), 'utf-8'))
  const linkedin = JSON.parse(readFileSync(join(REPO, 'scripts/linkedin/posts/schedule.json'), 'utf-8'))
  const taken = new Set(linkedin.map((p) => p.date))
  const clashes = manifest.articles.filter((a) => taken.has(a.date))
  assert.deepEqual(
    clashes.map((c) => `${c.slug} el ${c.date}`),
    [],
    'publicar un articulo dispara linkedin-post.yml: coincidir con schedule.json saca dos posts el mismo dia',
  )
})

test('ningun articulo del manifiesto comparte fecha con otro', () => {
  const manifest = JSON.parse(readFileSync(join(REPO, '.github/publish-schedule.json'), 'utf-8'))
  const byDate = new Map()
  for (const a of manifest.articles) {
    byDate.set(a.date, [...(byDate.get(a.date) ?? []), a.slug])
  }
  const doubled = [...byDate].filter(([, slugs]) => slugs.length > 1)
  assert.deepEqual(doubled, [], 'un articulo al dia')
})

test('CLI forced retry of an already published and pruned slug is a no-op', t => {
  const dir = mkdtempSync(join(tmpdir(), 'publish-retry-'))
  t.after(() => rmSync(dir, { recursive: true, force: true }))
  mkdirSync(join(dir, '.github'))
  mkdirSync(join(dir, 'src/content/blog/en'), { recursive: true })
  writeFileSync(join(dir, '.github/publish-schedule.json'), '{"articles":[]}')
  writeFileSync(join(dir, 'src/content/blog/en/published.md'), '# Published')
  const output = join(dir, 'outputs')
  const run = slug => spawnSync(process.execPath, [join(REPO, 'scripts/publish/select-due-article.mjs'), '--slug', slug], {
    cwd: dir, encoding: 'utf8', env: { ...process.env, GITHUB_OUTPUT: output },
  })
  const retry = run('published')
  assert.equal(retry.status, 0, retry.stderr)
  assert.match(retry.stdout, /ya esta en main/)
  assert.match(readFileSync(output, 'utf8'), /action=none/)
  const unknown = run('unknown')
  assert.equal(unknown.status, 2)
  assert.match(unknown.stderr, /no esta en/)
  assert.equal(run('../../../../published').status, 2)
})
