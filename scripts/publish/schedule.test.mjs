import { test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

const scripts = dirname(fileURLToPath(import.meta.url))
const api = await import('./schedule.mjs')
const entry = (slug, date = '2026-09-17', extra = {}) => ({
  slug, date, branch: `blog/${slug}`, article: `src/content/blog/en/${slug}.md`, ...extra,
})
const manifest = (...articles) => ({ _readme: ['Pending articles'], articles })
const a = entry('a'), b = entry('b', '2026-09-18'), c = entry('c', '2026-09-19')

test('schedule API is implemented', () => {
  assert.equal(typeof api.mergeSchedules, 'function')
  assert.equal(typeof api.pruneSchedule, 'function')
})

test('combines independent additions and sorts by date', () => {
  assert.deepEqual(api.mergeSchedules(manifest(a), manifest(c, a), manifest(a, b)), manifest(a, b, c))
})
test('identical additions and reordered JSON keys are not conflicts', () => {
  const reversed = Object.fromEntries(Object.entries(a).reverse())
  assert.deepEqual(api.mergeSchedules(manifest(), manifest(a), manifest(reversed)).articles, [a])
})
test('keeps one-sided edits and identical two-sided edits', () => {
  const changed = { ...a, date: '2026-09-20' }
  assert.deepEqual(api.mergeSchedules(manifest(a), manifest(changed), manifest(a)), manifest(changed))
  assert.deepEqual(api.mergeSchedules(manifest(a), manifest(a), manifest(changed)), manifest(changed))
  assert.deepEqual(api.mergeSchedules(manifest(a), manifest(changed), manifest(changed)), manifest(changed))
})
test('preserves deletions instead of resurrecting unchanged old entries', () => {
  assert.deepEqual(api.mergeSchedules(manifest(a, b), manifest(b), manifest(a, b, c)), manifest(b, c))
  assert.deepEqual(api.mergeSchedules(manifest(a, b), manifest(a, b, c), manifest(b)), manifest(b, c))
})
test('rejects incompatible edits and delete/edit disagreements', () => {
  assert.throws(() => api.mergeSchedules(manifest(a), manifest({ ...a, date: '2026-09-20' }), manifest({ ...a, date: '2026-09-21' })), /a.*conflict|conflict.*a/i)
  assert.throws(() => api.mergeSchedules(manifest(a), manifest(), manifest({ ...a, date: '2026-09-20' })), /conflict/i)
})
test('rejects two new articles on the same date', () => {
  assert.throws(() => api.mergeSchedules(manifest(), manifest(a), manifest(entry('other', a.date))), /date|fecha/i)
})
test('rejects malformed manifests and duplicate slugs before reconciling', () => {
  assert.throws(() => api.mergeSchedules(manifest(), { articles: 'bad' }, manifest()), /articles|manifest/i)
  assert.throws(() => api.mergeSchedules(manifest(), manifest(a, a), manifest()), /duplic/i)
})
test('preserves metadata edits and rejects incompatible metadata', () => {
  const changed = { ...manifest(a), _readme: ['New instructions'] }
  assert.deepEqual(api.mergeSchedules(manifest(a), changed, manifest(a, b)), { ...changed, articles: [a, b] })
  assert.throws(() => api.mergeSchedules(manifest(), { ...manifest(), version: 1 }, { ...manifest(), version: 2 }), /conflict/i)
})
test('already published entries cannot reappear or cause stale edit conflicts', () => {
  const isPublished = e => e.slug === 'a'
  assert.deepEqual(api.mergeSchedules(manifest(a), manifest(), manifest({ ...a, date: '2026-09-20' }, b), { isPublished }), manifest(b))
  assert.deepEqual(api.mergeSchedules(manifest(), manifest(b), manifest(a), { isPublished }), manifest(b))
})
test('prunes by article existence, never by elapsed date', () => {
  const late = entry('late', '2020-01-01')
  assert.deepEqual(api.pruneSchedule(manifest(a, late, b), e => e.slug === 'a'), manifest(late, b))
  assert.deepEqual(api.pruneSchedule(manifest(a), () => true), manifest())
})
test('cleanup rejects collisions with standalone LinkedIn posts', () => {
  assert.throws(() => api.pruneSchedule(manifest(a), () => false, [{ date: a.date }]), /LinkedIn/)
  assert.deepEqual(api.pruneSchedule(manifest(a), () => true, [{ date: a.date }]), manifest())
})

function fixture(t) {
  const dir = mkdtempSync(join(tmpdir(), 'publish-schedule-'))
  t.after(() => rmSync(dir, { recursive: true, force: true }))
  const run = (cmd, args) => spawnSync(cmd, args, { cwd: dir, encoding: 'utf8' })
  const git = (...args) => {
    const r = run('git', ['-c', `safe.directory=${dir.replaceAll('\\', '/')}`, ...args])
    assert.equal(r.status, 0, `${args.join(' ')}\n${r.stdout}\n${r.stderr}`)
    return r.stdout.trim()
  }
  const write = (path, content) => {
    mkdirSync(dirname(join(dir, path)), { recursive: true })
    writeFileSync(join(dir, path), content)
  }
  const save = value => write('.github/publish-schedule.json', JSON.stringify(value, null, 2) + '\n')
  const commit = msg => { git('add', '.'); git('commit', '-qm', msg) }
  git('init', '-q', '-b', 'main')
  git('config', 'user.name', 'test'); git('config', 'user.email', 'test@example.invalid')
  git('config', 'commit.gpgsign', 'false')
  git('config', 'merge.schedule.driver', `node "${join(scripts, 'merge-schedule.mjs').replaceAll('\\', '/')}" %O %A %B`)
  write('.gitattributes', '.github/publish-schedule.json merge=schedule\n')
  write('scripts/linkedin/posts/schedule.json', '[]\n')
  save(manifest(a)); commit('base')
  return { dir, run, git, write, save, commit }
}

test('real Git merge combines JSON and prunes in the publication commit', t => {
  const f = fixture(t)
  f.git('checkout', '-qb', 'blog/b')
  f.save(manifest(a, b)); f.write(b.article, '# B\n'); f.commit('article b')
  f.git('checkout', 'main'); f.save(manifest(a, c)); f.commit('schedule c')
  // Before implementation this fails: Git cannot resolve the JSON insertion.
  f.git('merge', '--no-ff', '--no-commit', 'blog/b')
  assert.deepEqual(JSON.parse(readFileSync(join(f.dir, '.github/publish-schedule.json'))), manifest(a, b, c))
  const result = f.run(process.execPath, [join(scripts, 'prune-schedule.mjs')])
  assert.equal(result.status, 0, result.stderr)
  f.git('add', '.github/publish-schedule.json'); f.git('commit', '-qm', 'Publish: b article')
  assert.deepEqual(JSON.parse(f.git('show', 'HEAD:.github/publish-schedule.json')), manifest(a, c))
  assert.equal(f.git('log', '-1', '--format=%s'), 'Publish: b article')
  assert.equal(f.git('status', '--porcelain'), '')
})

test('Git driver ignores already published articles in stale branches', t => {
  const f = fixture(t)
  f.git('checkout', '-qb', 'stale'); f.save(manifest({ ...a, date: '2026-09-20' }, b)); f.commit('stale schedule')
  f.git('checkout', 'main'); f.write(a.article, '# A\n'); f.save(manifest(c)); f.commit('published a')
  f.git('merge', '--no-ff', '--no-commit', 'stale')
  assert.deepEqual(JSON.parse(readFileSync(join(f.dir, '.github/publish-schedule.json'))), manifest(b, c))
})

test('Git driver rejects incompatible pending dates without overwriting our JSON', t => {
  const f = fixture(t)
  f.git('checkout', '-qb', 'conflict'); f.save(manifest({ ...a, date: '2026-09-20' })); f.commit('their date')
  f.git('checkout', 'main'); const ours = manifest({ ...a, date: '2026-09-21' }); f.save(ours); f.commit('our date')
  const result = f.run('git', ['-c', `safe.directory=${f.dir.replaceAll('\\', '/')}`, 'merge', '--no-ff', '--no-commit', 'conflict'])
  assert.notEqual(result.status, 0)
  assert.match(result.stderr, /conflict/i)
  assert.deepEqual(JSON.parse(readFileSync(join(f.dir, '.github/publish-schedule.json'))), ours)
})

test('cleanup ignores untracked drafts and validates the new article before removing it', t => {
  const f = fixture(t)
  f.write(a.article, '# Untracked draft\n')
  let result = f.run(process.execPath, [join(scripts, 'prune-schedule.mjs')])
  assert.equal(result.status, 0, result.stderr)
  assert.deepEqual(JSON.parse(readFileSync(join(f.dir, '.github/publish-schedule.json'))), manifest(a))
  // Simulate a textual merge that did not call the custom driver. Removing a
  // staged article must not hide a same-day collision before publication.
  f.git('add', a.article)
  f.save(manifest(a, entry('other', a.date)))
  result = f.run(process.execPath, [join(scripts, 'prune-schedule.mjs')])
  assert.notEqual(result.status, 0)
  assert.match(result.stderr, /date conflict/i)
})
