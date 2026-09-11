# Auditoría de vigencia de memorias — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clasificar las 35 memorias de `personal-website` en verdes (siguen siendo ciertas), rojas (afirman algo que ya no lo es) y grises (no admiten comprobación), para obtener el dato que sostiene el artículo 2.

**Architecture:** Un verificador en `scripts/memory-audit/` con la misma forma que el resto de scripts del repo: lógica pura exportada y probada con `node:test`, CLI al final del módulo que la orquesta. Las comprobaciones se declaran en el frontmatter de cada memoria con un vocabulario cerrado que **interpreta el verificador**; nunca se ejecuta shell. Las memorias viven fuera del repositorio (`~/.claude/projects/<proyecto>/memory/`), así que el directorio es un parámetro y lo único que entra en git es el verificador y los agregados.

**Tech Stack:** Node 22 ESM (`.mjs`), `node:test`, `node:assert/strict`, `node:fs`. Sin dependencias nuevas.

**Spec:** [`../specs/2026-09-11-dos-regimenes-de-memoria-design.md`](../specs/2026-09-11-dos-regimenes-de-memoria-design.md) §4

## Global Constraints

- **Nunca ejecutar shell ni código desde una memoria.** El vocabulario es cerrado: `file_exists`, `file_absent`, `file_contains`, `date_passed`. Cualquier clave desconocida es un error de la memoria, no una extensión.
- **Ninguna ruta puede salir del repositorio.** Toda ruta declarada en una memoria se resuelve contra la raíz del repo y se rechaza si escapa.
- **Glob mínimo:** solo `*` dentro de un único segmento de ruta. Sin `**`, sin `?`, sin llaves. Se implementa a mano para no depender de `fs.globSync`, que sigue siendo experimental.
- **Lo que entra en git es el verificador y los agregados.** El contenido de las memorias es privado y no se commitea (§6 de la spec).
- **Idioma:** comentarios y tests en español, sin tildes dentro de comentarios de código, como el resto de `scripts/`.
- **Predicción registrada antes de correr la auditoría** (§4.4 de la spec): el montón gris será el mayor y el rojo pequeño pero no cero. Se escribe en el informe *antes* de ver el resultado.

---

## File Structure

| Fichero | Responsabilidad |
|---|---|
| `scripts/memory-audit/checks.mjs` | Vocabulario de comprobaciones. Evalúa una comprobación contra el disco. |
| `scripts/memory-audit/checks.test.mjs` | Tests del vocabulario, incluida la seguridad de rutas. |
| `scripts/memory-audit/parse-memory.mjs` | Lee un fichero de memoria: frontmatter, tipo y comprobaciones declaradas. |
| `scripts/memory-audit/parse-memory.test.mjs` | Tests del parseo. |
| `scripts/memory-audit/audit.mjs` | Clasifica en verde/rojo/gris, agrega y formatea. CLI al final. |
| `scripts/memory-audit/audit.test.mjs` | Tests de clasificación, agregados y formato. |

---

### Task 1: Vocabulario de comprobaciones

**Files:**
- Create: `scripts/memory-audit/checks.mjs`
- Test: `scripts/memory-audit/checks.test.mjs`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `resolveInRepo(repoRoot: string, relPath: string) -> string` — ruta absoluta; lanza `Error` si escapa del repo.
  - `matchGlob(pattern: string, name: string) -> boolean` — solo `*`.
  - `runCheck(check: object, ctx: { repoRoot: string, today: string }) -> { ok: boolean, reason: string }` — lanza `Error` si la clave es desconocida.

- [ ] **Step 1: Write the failing test**

```javascript
// scripts/memory-audit/checks.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, writeFileSync, mkdirSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { resolveInRepo, matchGlob, runCheck } from './checks.mjs'

const repo = () => {
  const dir = mkdtempSync(join(tmpdir(), 'memaudit-'))
  mkdirSync(join(dir, '.github', 'workflows'), { recursive: true })
  writeFileSync(join(dir, '.github', 'publish-schedule.json'), '{}')
  writeFileSync(join(dir, 'config.ts'), 'export const linkedinLinks = []')
  return dir
}

const ctx = (root) => ({ repoRoot: root, today: '2026-09-11' })

test('resolveInRepo rechaza rutas que salen del repo', () => {
  const root = repo()
  assert.throws(() => resolveInRepo(root, '../../etc/passwd'), /fuera del repositorio/)
})

test('resolveInRepo acepta una ruta interna', () => {
  const root = repo()
  assert.equal(resolveInRepo(root, 'config.ts'), join(root, 'config.ts'))
})

test('matchGlob solo entiende asterisco simple', () => {
  assert.equal(matchGlob('scheduled-publish-*.yml', 'scheduled-publish-x.yml'), true)
  assert.equal(matchGlob('scheduled-publish-*.yml', 'otro.yml'), false)
  assert.equal(matchGlob('exacto.yml', 'exacto.yml'), true)
})

test('file_exists pasa cuando el fichero esta', () => {
  const root = repo()
  const r = runCheck({ file_exists: '.github/publish-schedule.json' }, ctx(root))
  assert.equal(r.ok, true)
})

test('file_exists falla cuando el fichero no esta', () => {
  const root = repo()
  const r = runCheck({ file_exists: 'no-existe.json' }, ctx(root))
  assert.equal(r.ok, false)
})

test('file_absent pasa cuando ningun fichero casa con el glob', () => {
  const root = repo()
  const r = runCheck({ file_absent: '.github/workflows/scheduled-publish-*.yml' }, ctx(root))
  assert.equal(r.ok, true)
})

test('file_absent falla cuando existe un fichero que casa', () => {
  const root = repo()
  writeFileSync(join(root, '.github', 'workflows', 'scheduled-publish-x.yml'), '')
  const r = runCheck({ file_absent: '.github/workflows/scheduled-publish-*.yml' }, ctx(root))
  assert.equal(r.ok, false)
})

test('file_contains detecta el texto', () => {
  const root = repo()
  const r = runCheck({ file_contains: { path: 'config.ts', text: 'linkedinLinks' } }, ctx(root))
  assert.equal(r.ok, true)
})

test('file_contains falla si el fichero no existe', () => {
  const root = repo()
  const r = runCheck({ file_contains: { path: 'nada.ts', text: 'x' } }, ctx(root))
  assert.equal(r.ok, false)
})

test('date_passed compara contra today', () => {
  const root = repo()
  assert.equal(runCheck({ date_passed: '2026-09-01' }, ctx(root)).ok, true)
  assert.equal(runCheck({ date_passed: '2026-12-01' }, ctx(root)).ok, false)
})

test('una clave desconocida es un error, no una extension', () => {
  const root = repo()
  assert.throws(() => runCheck({ run_shell: 'rm -rf /' }, ctx(root)), /desconocida/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test scripts/memory-audit/checks.test.mjs`
Expected: FAIL — `Cannot find module './checks.mjs'`

- [ ] **Step 3: Write minimal implementation**

```javascript
// scripts/memory-audit/checks.mjs
// Vocabulario cerrado de comprobaciones de vigencia.
//
// Lo interpreta este modulo; NUNCA se ejecuta shell. Una memoria la escribe
// un agente, asi que un comando arbitrario dentro de ella seria ejecucion
// arbitraria. Ver docs/superpowers/specs/2026-09-11-dos-regimenes-de-memoria-design.md

import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { resolve, sep, dirname, basename } from 'node:path'

/** Resuelve una ruta relativa contra la raiz del repo y prohibe salir de ella. */
export function resolveInRepo(repoRoot, relPath) {
  const root = resolve(repoRoot)
  const target = resolve(root, relPath)
  if (target !== root && !target.startsWith(root + sep)) {
    throw new Error(`ruta fuera del repositorio: ${relPath}`)
  }
  return target
}

/** Glob minimo: solo "*", dentro de un unico segmento. */
export function matchGlob(pattern, name) {
  const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '[^/]*')
  return new RegExp(`^${escaped}$`).test(name)
}

function anyFileMatches(repoRoot, pattern) {
  const dir = dirname(pattern)
  const base = basename(pattern)
  const abs = resolveInRepo(repoRoot, dir)
  if (!existsSync(abs)) return false
  return readdirSync(abs).some((name) => matchGlob(base, name))
}

/** Evalua una comprobacion. Devuelve {ok, reason}; lanza si la clave no existe. */
export function runCheck(check, { repoRoot, today }) {
  if ('file_exists' in check) {
    const ok = existsSync(resolveInRepo(repoRoot, check.file_exists))
    return { ok, reason: ok ? `existe ${check.file_exists}` : `no existe ${check.file_exists}` }
  }
  if ('file_absent' in check) {
    const found = anyFileMatches(repoRoot, check.file_absent)
    return { ok: !found, reason: found ? `todavia existe algo que casa con ${check.file_absent}` : `no hay nada que case con ${check.file_absent}` }
  }
  if ('file_contains' in check) {
    const { path, text } = check.file_contains
    const abs = resolveInRepo(repoRoot, path)
    if (!existsSync(abs)) return { ok: false, reason: `no existe ${path}` }
    const ok = readFileSync(abs, 'utf8').includes(text)
    return { ok, reason: ok ? `${path} contiene "${text}"` : `${path} ya no contiene "${text}"` }
  }
  if ('date_passed' in check) {
    const ok = check.date_passed <= today
    return { ok, reason: ok ? `${check.date_passed} ya paso` : `${check.date_passed} aun no ha llegado` }
  }
  throw new Error(`comprobacion desconocida: ${Object.keys(check).join(', ')}`)
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test scripts/memory-audit/checks.test.mjs`
Expected: PASS — 11 tests

- [ ] **Step 5: Commit**

```bash
git add scripts/memory-audit/checks.mjs scripts/memory-audit/checks.test.mjs
git commit -m "memory-audit: vocabulario cerrado de comprobaciones de vigencia"
```

---

### Task 2: Parseo de memorias

**Files:**
- Create: `scripts/memory-audit/parse-memory.mjs`
- Test: `scripts/memory-audit/parse-memory.test.mjs`

**Interfaces:**
- Consumes: nada de Task 1.
- Produces:
  - `parseMemory(raw: string, name: string) -> { name, type: string|null, checks: object[], revalidate: string|null, errors: string[] }`

Una memoria sin `checks` no es un error: es una candidata a gris. `revalidate` es la pregunta en texto libre del §4.3 de la spec, que se reporta pero no se evalúa.

- [ ] **Step 1: Write the failing test**

```javascript
// scripts/memory-audit/parse-memory.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'

import { parseMemory } from './parse-memory.mjs'

const conChecks = `---
name: project_blog_publishing_mechanism
description: "Como se publican los articulos"
metadata:
  type: project
checks:
  - file_exists: .github/publish-schedule.json
  - file_absent: .github/workflows/scheduled-publish-*.yml
---

Cuerpo de la memoria.
`

const sinChecks = `---
name: feedback_narrate_shell_commands
description: "Narrar los comandos"
metadata:
  type: feedback
---

Cuerpo.
`

const conRevalidate = `---
name: project_x
metadata:
  type: project
revalidate: "Sigue siendo el gateway el mismo?"
---

Cuerpo.
`

test('extrae tipo y comprobaciones', () => {
  const m = parseMemory(conChecks, 'project_blog_publishing_mechanism.md')
  assert.equal(m.type, 'project')
  assert.equal(m.checks.length, 2)
  assert.deepEqual(m.checks[0], { file_exists: '.github/publish-schedule.json' })
  assert.deepEqual(m.errors, [])
})

test('una memoria sin checks no es un error', () => {
  const m = parseMemory(sinChecks, 'feedback_narrate_shell_commands.md')
  assert.equal(m.checks.length, 0)
  assert.deepEqual(m.errors, [])
  assert.equal(m.type, 'feedback')
})

test('recoge la pregunta de revalidacion sin evaluarla', () => {
  const m = parseMemory(conRevalidate, 'project_x.md')
  assert.equal(m.revalidate, 'Sigue siendo el gateway el mismo?')
  assert.equal(m.checks.length, 0)
})

test('el tipo ausente se reporta como null, no revienta', () => {
  const m = parseMemory('---\nname: x\n---\n\nCuerpo.\n', 'x.md')
  assert.equal(m.type, null)
})

test('un fichero sin frontmatter produce un error legible', () => {
  const m = parseMemory('solo cuerpo\n', 'roto.md')
  assert.equal(m.errors.length, 1)
  assert.match(m.errors[0], /frontmatter/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test scripts/memory-audit/parse-memory.test.mjs`
Expected: FAIL — `Cannot find module './parse-memory.mjs'`

- [ ] **Step 3: Write minimal implementation**

```javascript
// scripts/memory-audit/parse-memory.mjs
// Lee una memoria de Claude Code: frontmatter, tipo y comprobaciones.
//
// Parseo a mano y deliberadamente estrecho: el frontmatter de estas memorias
// es plano y conocido, y meter un parser de YAML completo para esto seria
// traer una dependencia y una superficie de ataque que no hacen falta.

const FRONTMATTER = /^---\n([\s\S]*?)\n---/

function parseCheckLine(line) {
  // "- file_exists: ruta"  |  "- file_contains: { path: x, text: y }"
  const m = line.match(/^\s*-\s*([a-z_]+):\s*(.+)$/)
  if (!m) return null
  const [, key, rawValue] = m
  const value = rawValue.trim()
  if (value.startsWith('{')) {
    const obj = {}
    for (const pair of value.replace(/^\{|\}$/g, '').split(',')) {
      const [k, ...rest] = pair.split(':')
      if (!k || rest.length === 0) continue
      obj[k.trim()] = rest.join(':').trim().replace(/^["']|["']$/g, '')
    }
    return { [key]: obj }
  }
  return { [key]: value.replace(/^["']|["']$/g, '') }
}

export function parseMemory(raw, name) {
  const errors = []
  const fm = raw.match(FRONTMATTER)
  if (!fm) {
    return { name, type: null, checks: [], revalidate: null, errors: ['sin frontmatter'] }
  }
  const head = fm[1]

  const typeMatch = head.match(/^\s+type:\s*(.+)$/m)
  const type = typeMatch ? typeMatch[1].trim() : null

  const revalidateMatch = head.match(/^revalidate:\s*(.+)$/m)
  const revalidate = revalidateMatch
    ? revalidateMatch[1].trim().replace(/^["']|["']$/g, '')
    : null

  const checks = []
  const checksStart = head.match(/^checks:\s*$/m)
  if (checksStart) {
    const after = head.slice(head.indexOf(checksStart[0]) + checksStart[0].length)
    for (const line of after.split('\n')) {
      if (!/^\s*-\s/.test(line)) break
      const parsed = parseCheckLine(line)
      if (parsed) checks.push(parsed)
      else errors.push(`comprobacion ilegible: ${line.trim()}`)
    }
  }

  return { name, type, checks, revalidate, errors }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test scripts/memory-audit/parse-memory.test.mjs`
Expected: PASS — 5 tests

- [ ] **Step 5: Commit**

```bash
git add scripts/memory-audit/parse-memory.mjs scripts/memory-audit/parse-memory.test.mjs
git commit -m "memory-audit: parseo de memorias y sus comprobaciones"
```

---

### Task 3: Clasificación y agregados

**Files:**
- Create: `scripts/memory-audit/audit.mjs`
- Test: `scripts/memory-audit/audit.test.mjs`

**Interfaces:**
- Consumes: `runCheck` de Task 1, `parseMemory` de Task 2.
- Produces:
  - `classify(memory: object, ctx: { repoRoot, today }, run = runCheck) -> { name, state: 'verde'|'rojo'|'gris'|'error', failures: string[] }`
  - `summarise(results: object[]) -> { verde: number, rojo: number, gris: number, error: number, total: number }`

Reglas: sin comprobaciones → `gris`. Con comprobaciones y todas pasan → `verde`. Alguna falla → `rojo`. Comprobación ilegible o desconocida → `error` (ni verde ni rojo: un fallo del verificador no puede contarse como memoria obsoleta).

- [ ] **Step 1: Write the failing test**

```javascript
// scripts/memory-audit/audit.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'

import { classify, summarise } from './audit.mjs'

const ctx = { repoRoot: '/tmp/no-se-usa', today: '2026-09-11' }
const siempreOk = () => ({ ok: true, reason: 'ok' })
const siempreFalla = () => ({ ok: false, reason: 'ya no existe' })

const mem = (over = {}) => ({ name: 'm.md', type: 'project', checks: [], revalidate: null, errors: [], ...over })

test('sin comprobaciones es gris', () => {
  const r = classify(mem(), ctx, siempreOk)
  assert.equal(r.state, 'gris')
})

test('todas las comprobaciones pasan: verde', () => {
  const r = classify(mem({ checks: [{ file_exists: 'a' }, { file_exists: 'b' }] }), ctx, siempreOk)
  assert.equal(r.state, 'verde')
  assert.deepEqual(r.failures, [])
})

test('una comprobacion que falla pinta la memoria de rojo', () => {
  const r = classify(mem({ checks: [{ file_exists: 'a' }] }), ctx, siempreFalla)
  assert.equal(r.state, 'rojo')
  assert.equal(r.failures.length, 1)
})

test('una memoria ilegible es error, no rojo', () => {
  const r = classify(mem({ errors: ['sin frontmatter'] }), ctx, siempreOk)
  assert.equal(r.state, 'error')
})

test('una comprobacion desconocida es error, no rojo', () => {
  const explota = () => { throw new Error('comprobacion desconocida: run_shell') }
  const r = classify(mem({ checks: [{ run_shell: 'x' }] }), ctx, explota)
  assert.equal(r.state, 'error')
})

test('summarise cuenta cada monton', () => {
  const s = summarise([
    { state: 'verde' }, { state: 'verde' }, { state: 'rojo' }, { state: 'gris' }, { state: 'error' },
  ])
  assert.deepEqual(s, { verde: 2, rojo: 1, gris: 1, error: 1, total: 5 })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test scripts/memory-audit/audit.test.mjs`
Expected: FAIL — `Cannot find module './audit.mjs'`

- [ ] **Step 3: Write minimal implementation**

```javascript
// scripts/memory-audit/audit.mjs
// Clasifica cada memoria en verde / rojo / gris. Ver el plan en
// docs/superpowers/plans/2026-09-11-auditoria-vigencia-memorias.md

import { runCheck } from './checks.mjs'

/**
 * Clasifica una memoria ya parseada.
 * `run` es inyectable para poder probar la clasificacion sin tocar disco.
 */
export function classify(memory, ctx, run = runCheck) {
  if (memory.errors.length > 0) {
    return { name: memory.name, state: 'error', failures: memory.errors }
  }
  if (memory.checks.length === 0) {
    return { name: memory.name, state: 'gris', failures: [] }
  }
  const failures = []
  for (const check of memory.checks) {
    let result
    try {
      result = run(check, ctx)
    } catch (err) {
      return { name: memory.name, state: 'error', failures: [err.message] }
    }
    if (!result.ok) failures.push(result.reason)
  }
  return {
    name: memory.name,
    state: failures.length > 0 ? 'rojo' : 'verde',
    failures,
  }
}

export function summarise(results) {
  const s = { verde: 0, rojo: 0, gris: 0, error: 0, total: results.length }
  for (const r of results) s[r.state] += 1
  return s
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test scripts/memory-audit/audit.test.mjs`
Expected: PASS — 6 tests

- [ ] **Step 5: Commit**

```bash
git add scripts/memory-audit/audit.mjs scripts/memory-audit/audit.test.mjs
git commit -m "memory-audit: clasificacion en verde, rojo y gris"
```

---

### Task 4: CLI e informe

**Files:**
- Modify: `scripts/memory-audit/audit.mjs` (añadir formateador y CLI al final)
- Modify: `scripts/memory-audit/audit.test.mjs` (añadir tests del formateador)
- Modify: `package.json` (añadir script `audit:memory`)

**Interfaces:**
- Consumes: `classify`, `summarise` de Task 3; `parseMemory` de Task 2.
- Produces:
  - `formatReport(results: object[], summary: object) -> string` — informe en texto, **sin contenido de las memorias**: solo nombre de fichero, estado y motivo del fallo.

El informe nombra ficheros y motivos, nunca el cuerpo de la memoria: §6 de la spec.

- [ ] **Step 1: Write the failing test**

Añadir `formatReport` al import que ya existe en la cabecera del fichero, que
pasa a ser `import { classify, summarise, formatReport } from './audit.mjs'`, y
después estos dos tests:

```javascript
// añadir a scripts/memory-audit/audit.test.mjs
test('el informe lista las rojas con su motivo', () => {
  const results = [
    { name: 'a.md', state: 'verde', failures: [] },
    { name: 'b.md', state: 'rojo', failures: ['no existe x.yml'] },
    { name: 'c.md', state: 'gris', failures: [] },
  ]
  const out = formatReport(results, summarise(results))
  assert.match(out, /b\.md/)
  assert.match(out, /no existe x\.yml/)
  assert.match(out, /verde:\s*1/)
  assert.match(out, /rojo:\s*1/)
  assert.match(out, /gris:\s*1/)
})

test('el informe no incluye el cuerpo de ninguna memoria', () => {
  const results = [{ name: 'a.md', state: 'gris', failures: [], body: 'SECRETO' }]
  const out = formatReport(results, summarise(results))
  assert.equal(out.includes('SECRETO'), false)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test scripts/memory-audit/audit.test.mjs`
Expected: FAIL — `formatReport is not a function`

- [ ] **Step 3: Write minimal implementation**

```javascript
// añadir al final de scripts/memory-audit/audit.mjs

/** Informe en texto. Solo nombres, estados y motivos: nunca el cuerpo. */
export function formatReport(results, summary) {
  const lines = []
  lines.push('# Auditoria de vigencia de memorias')
  lines.push('')
  lines.push(`total: ${summary.total}`)
  lines.push(`verde: ${summary.verde}   (la comprobacion pasa)`)
  lines.push(`rojo: ${summary.rojo}   (afirma algo que ya no es cierto)`)
  lines.push(`gris: ${summary.gris}   (no admite comprobacion)`)
  lines.push(`error: ${summary.error}   (memoria o comprobacion ilegible)`)
  lines.push('')
  const rojas = results.filter((r) => r.state === 'rojo')
  if (rojas.length > 0) {
    lines.push('## Rojas')
    for (const r of rojas) {
      lines.push(`- ${r.name}`)
      for (const f of r.failures) lines.push(`    ${f}`)
    }
    lines.push('')
  }
  const errores = results.filter((r) => r.state === 'error')
  if (errores.length > 0) {
    lines.push('## Errores')
    for (const r of errores) lines.push(`- ${r.name}: ${r.failures.join('; ')}`)
    lines.push('')
  }
  return lines.join('\n')
}

// --- CLI ---------------------------------------------------------------
// node scripts/memory-audit/audit.mjs --memory-dir <ruta> [--repo-root <ruta>]
if (import.meta.url === `file://${process.argv[1]}`) {
  const { readdirSync, readFileSync } = await import('node:fs')
  const { join } = await import('node:path')
  const { parseMemory } = await import('./parse-memory.mjs')

  const arg = (name, fallback) => {
    const i = process.argv.indexOf(name)
    return i === -1 ? fallback : process.argv[i + 1]
  }
  const memoryDir = arg('--memory-dir')
  if (!memoryDir) {
    console.error('falta --memory-dir')
    process.exit(2)
  }
  const repoRoot = arg('--repo-root', process.cwd())
  const today = new Date().toISOString().slice(0, 10)

  const results = readdirSync(memoryDir)
    .filter((f) => f.endsWith('.md') && f !== 'MEMORY.md')
    .map((f) => classify(parseMemory(readFileSync(join(memoryDir, f), 'utf8'), f), { repoRoot, today }))

  console.log(formatReport(results, summarise(results)))
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test scripts/memory-audit/audit.test.mjs`
Expected: PASS — 8 tests

- [ ] **Step 5: Añadir el script a package.json**

En `scripts`, junto a `test`:

```json
"audit:memory": "node scripts/memory-audit/audit.mjs"
```

- [ ] **Step 6: Verificar la suite completa**

Run: `npm test`
Expected: PASS — los tests nuevos más los que ya existían, sin regresiones.

- [ ] **Step 7: Commit**

```bash
git add scripts/memory-audit/audit.mjs scripts/memory-audit/audit.test.mjs package.json
git commit -m "memory-audit: informe y CLI"
```

---

### Task 5: Proponer comprobaciones para las 35 memorias

**Files:**
- Modify: los ficheros de `~/.claude/projects/-Users-javieraguilarmartin1-Documents-repos-personal-website/memory/*.md` (**fuera del repositorio; no se commitean**)
- Create: `docs/superpowers/plans/2026-09-11-checks-propuestos.md` (tabla de propuestas para revisión humana, **sin cuerpo de memorias**)

**Interfaces:**
- Consumes: el vocabulario de Task 1.
- Produces: memorias con bloque `checks:` en su frontmatter, listas para Task 6.

Este es el paso semiautomático de §4.2 de la spec. La revisión humana **es parte del experimento**: mide cuántas memorias admiten comprobación sin forzarla.

- [ ] **Step 1: Recorrer cada memoria y proponer**

Para cada uno de los 35 ficheros, leer la memoria y decidir:
- ¿afirma algo sobre el estado del repositorio que pueda caducar solo? → proponer `checks`;
- ¿es una preferencia, un criterio o una intención? → **no proponer nada**; es gris por diseño (§2 de la spec).

Volcar las propuestas en `docs/superpowers/plans/2026-09-11-checks-propuestos.md` con una fila por memoria: nombre, comprobación propuesta (o «gris») y una línea de justificación. Sin copiar el cuerpo de las memorias.

- [ ] **Step 2: Revisión humana**

Presentar la tabla al autor. Él acepta, corrige o rechaza cada propuesta. Una comprobación forzada es peor que ninguna: infla el verde y falsea el resultado.

- [ ] **Step 3: Aplicar las aceptadas**

Escribir el bloque `checks:` en el frontmatter de cada memoria aceptada, después de `metadata:`:

```yaml
checks:
  - file_exists: .github/publish-schedule.json
  - file_absent: .github/workflows/scheduled-publish-*.yml
```

- [ ] **Step 4: Verificar que el parseo las lee**

Run: `npm run audit:memory -- --memory-dir ~/.claude/projects/-Users-javieraguilarmartin1-Documents-repos-personal-website/memory`
Expected: el recuento de `gris` baja respecto a la primera ejecución y `error` es 0.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-09-11-checks-propuestos.md
git commit -m "memory-audit: comprobaciones propuestas y revisadas para las 35 memorias"
```

---

### Task 6: Correr la auditoría y registrar el resultado

**Files:**
- Create: `docs/superpowers/specs/2026-09-11-auditoria-resultados.md`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: el dato que sostiene el artículo 2.

- [ ] **Step 1: Registrar la predicción ANTES de correr**

Escribir la cabecera del documento de resultados con la predicción de §4.4 de la spec, antes de ver ninguna salida:

> Predicción registrada el 2026-09-11, antes de ejecutar: el montón gris será el
> mayor y el rojo será pequeño pero no cero. Si el rojo sale en cero, la tesis del
> artículo se debilita y hay que decirlo.

- [ ] **Step 2: Ejecutar**

Run: `npm run audit:memory -- --memory-dir ~/.claude/projects/-Users-javieraguilarmartin1-Documents-repos-personal-website/memory > /tmp/audit.txt`
Expected: informe con los cuatro recuentos y la lista de rojas.

- [ ] **Step 3: Comprobar a mano cada roja**

Una roja es una acusación: hay que verificar que la memoria está de verdad obsoleta y que no es la comprobación la que está mal escrita. Para cada una, leer la memoria y confirmar contra el repositorio. Las falsas rojas se corrigen en Task 5 y se vuelve a ejecutar.

Caso ya conocido que debe salir en rojo: `project_blog_publishing_mechanism`, que afirma el mecanismo de workflows de un solo uso (§3 de la spec).

- [ ] **Step 4: Escribir los resultados**

Completar `docs/superpowers/specs/2026-09-11-auditoria-resultados.md` con: los cuatro recuentos, la tabla de rojas con su motivo verificado, el reparto de grises por tipo de memoria, y si la predicción se cumplió o no. **Sin cuerpo de memorias** (§6 de la spec).

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-09-11-auditoria-resultados.md
git commit -m "memory-audit: resultados de la auditoria sobre las 35 memorias"
```

---

## Self-Review

**Cobertura de la spec §4:**

| Requisito de la spec | Tarea |
|---|---|
| §4.1 entrada: 35 memorias | Task 6 Step 2 (CLI recorre el directorio, excluye `MEMORY.md`) |
| §4.2 paso previo: proponer checks + revisión humana | Task 5 |
| §4.3 vocabulario declarativo, nunca shell | Task 1 |
| §4.3 escape a pregunta de revalidación no determinista | Task 2 (`revalidate`, se reporta y no se evalúa) |
| §4.4 tres montones | Task 3 |
| §4.4 predicción registrada antes de correr | Task 6 Step 1 |
| §6 anonimización: solo agregados | Task 4 (`formatReport` con test que lo fuerza) |

**Consistencia de nombres:** `runCheck`, `parseMemory`, `classify`, `summarise`, `formatReport`, `resolveInRepo`, `matchGlob` se usan con la misma firma en todas las tareas.

**Estado `error` como cuarto montón:** la spec habla de tres, pero una comprobación mal escrita no puede contarse como memoria obsoleta —inflaría el resultado justo en la dirección que nos conviene—, así que se separa. Task 6 Step 3 exige que `error` sea 0 antes de dar el resultado por bueno.
