// scripts/memory-audit/load-checks.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { VOCABULARIO as VOCABULARIO_CHECKS } from './checks.mjs'
import { loadChecks, VOCABULARIO } from './load-checks.mjs'

const AQUI = dirname(fileURLToPath(import.meta.url))

/** Azucar: el JSON de un checks.json con las entradas que se le pasen. */
function json(memories, extra = {}) {
  return JSON.stringify({ _readme: ['comentario'], memories, ...extra })
}

// --- forma general --------------------------------------------------------

test('carga una entrada valida y la indexa por nombre de memoria', () => {
  const { entries, errors } = loadChecks(
    json({ project_x: { checks: [{ file_exists: 'a.txt' }] } }),
  )
  assert.deepEqual(errors, [])
  assert.equal(entries.size, 1)
  const e = entries.get('project_x')
  assert.deepEqual(e.checks, [{ file_exists: 'a.txt' }])
  assert.deepEqual(e.errors, [])
  assert.equal(e.revalidate, null)
})

test('acepta las cuatro comprobaciones del vocabulario', () => {
  const { errors } = loadChecks(
    json({
      m: {
        checks: [
          { file_exists: 'a' },
          { file_absent: 'b/*.yml' },
          { file_contains: { path: 'c', text: 'd' } },
          { date_passed: '2026-01-01' },
        ],
      },
    }),
  )
  assert.deepEqual(errors, [])
})

test('una entrada solo con revalidate es valida y no tiene comprobaciones', () => {
  const { entries, errors } = loadChecks(json({ m: { revalidate: 'sigue siendo asi?' } }))
  assert.deepEqual(errors, [])
  assert.deepEqual(entries.get('m').checks, [])
  assert.equal(entries.get('m').revalidate, 'sigue siendo asi?')
})

// --- JSON invalido: error limpio, nunca excepcion sin capturar ------------

test('un JSON invalido es un error limpio y fatal, no una excepcion', () => {
  const r = loadChecks('{ esto no es json')
  assert.equal(r.fatal, true)
  assert.equal(r.entries.size, 0)
  assert.equal(r.errors.length, 1)
  assert.match(r.errors[0], /JSON invalido/)
})

test('una raiz que no es objeto es fatal', () => {
  for (const raw of ['[]', '"texto"', '42', 'null']) {
    const r = loadChecks(raw)
    assert.equal(r.fatal, true, `deberia ser fatal: ${raw}`)
  }
})

test('sin la clave memories es fatal: no se puede clasificar nada', () => {
  const r = loadChecks('{"_readme":["x"]}')
  assert.equal(r.fatal, true)
  assert.match(r.errors.join(' '), /memories/)
})

test('una entrada que no es texto es fatal', () => {
  const r = loadChecks({ memories: {} })
  assert.equal(r.fatal, true)
})

// --- severidad: lo dudoso va a errors, nunca se acepta callando -----------

test('una clave que no parece nombre de memoria va a errors y no entra en el mapa', () => {
  const { entries, errors } = loadChecks(
    json({ '../../etc/passwd': { checks: [{ file_exists: 'a' }] } }),
  )
  assert.equal(entries.size, 0)
  assert.equal(errors.length, 1)
  assert.match(errors[0], /no plausible/)
})

test('tampoco son plausibles las claves con barras, saltos de linea o vacias', () => {
  for (const clave of ['a/b', 'a\nb', '', '.oculta', 'x'.repeat(200)]) {
    const { entries, errors } = loadChecks(json({ [clave]: { checks: [{ file_exists: 'a' }] } }))
    assert.equal(entries.size, 0, `no deberia entrar: ${JSON.stringify(clave)}`)
    assert.equal(errors.length, 1)
  }
})

test('checks vacio es error de la entrada, no una memoria gris', () => {
  const { entries, errors } = loadChecks(json({ m: { checks: [] } }))
  assert.equal(errors.length, 1)
  assert.ok(entries.get('m').errors.length > 0, 'la entrada tiene que llevar su propio error')
})

test('checks que no es array es error de la entrada', () => {
  const { entries } = loadChecks(json({ m: { checks: { file_exists: 'a' } } }))
  assert.ok(entries.get('m').errors.length > 0)
})

test('una comprobacion con dos claves es error: no se elige una a dedo', () => {
  const { entries, errors } = loadChecks(
    json({ m: { checks: [{ file_exists: 'a', file_absent: 'b' }] } }),
  )
  assert.ok(errors.length > 0)
  assert.match(errors.join(' '), /clave/)
  assert.ok(entries.get('m').errors.length > 0)
  assert.deepEqual(entries.get('m').checks, [], 'una comprobacion ambigua no se ejecuta')
})

test('una comprobacion fuera del vocabulario es error', () => {
  const { entries, errors } = loadChecks(json({ m: { checks: [{ run_shell: 'rm -rf /' }] } }))
  assert.match(errors.join(' '), /desconocida/)
  assert.ok(entries.get('m').errors.length > 0)
})

test('una comprobacion que no es objeto es error', () => {
  for (const check of ['file_exists', 42, null, ['file_exists']]) {
    const { entries } = loadChecks(json({ m: { checks: [check] } }))
    assert.ok(entries.get('m').errors.length > 0, `deberia fallar: ${JSON.stringify(check)}`)
  }
})

test('revalidate que no es string es error de la entrada', () => {
  const { entries, errors } = loadChecks(json({ m: { revalidate: ['pregunta'] } }))
  assert.match(errors.join(' '), /revalidate/)
  assert.ok(entries.get('m').errors.length > 0)
})

test('una entrada que no es objeto es error de esa entrada, no fatal', () => {
  const r = loadChecks(json({ m: [{ file_exists: 'a' }] }))
  assert.equal(r.fatal, false)
  assert.ok(r.entries.get('m').errors.length > 0)
})

test('una clave desconocida dentro de la entrada es error', () => {
  const { entries } = loadChecks(json({ m: { checks: [{ file_exists: 'a' }], chekcs: [] } }))
  assert.ok(entries.get('m').errors.length > 0, 'una errata en el nombre del campo no puede pasar callada')
})

test('una clave de primer nivel desconocida se reporta pero no impide cargar', () => {
  const { entries, errors } = loadChecks(
    json({ m: { checks: [{ file_exists: 'a' }] } }, { memorias: {} }),
  )
  assert.equal(entries.size, 1)
  assert.match(errors.join(' '), /primer nivel/)
})

test('una entrada invalida no contamina a las demas', () => {
  const { entries } = loadChecks(
    json({ buena: { checks: [{ file_exists: 'a' }] }, mala: { checks: [{ run_shell: 'x' }] } }),
  )
  assert.deepEqual(entries.get('buena').errors, [])
  assert.ok(entries.get('mala').errors.length > 0)
})

test('__proto__ como clave no es un nombre de memoria plausible ni ensucia el prototipo', () => {
  const { entries, errors } = loadChecks('{"memories":{"__proto__":{"checks":[{"file_exists":"a"}]}}}')
  assert.equal(errors.length, 1)
  assert.equal(entries.size, 0)
  assert.equal({}.checks, undefined)
})

// --- el checks.json que se commitea tiene que cargar limpio ---------------

test('el checks.json del repositorio carga sin errores', () => {
  const raw = readFileSync(join(AQUI, 'checks.json'), 'utf8')
  const { entries, errors, fatal } = loadChecks(raw)
  assert.equal(fatal, false)
  assert.deepEqual(errors, [])
  assert.ok(entries.size > 0, 'deberia traer al menos la entrada del caso conocido')
  for (const [nombre, entrada] of entries) {
    assert.deepEqual(entrada.errors, [], `entrada con errores: ${nombre}`)
  }
})

// --- una sola fuente de verdad para la forma de una comprobacion ----------
// El cargador tenia su propia copia del vocabulario y su propio validador, que
// solo miraba la clave y nunca el valor: una entrada con valor invalido pasaba
// la carga y solo reventaba al ejecutarse, ya dentro de la auditoria.

test('el vocabulario del cargador es el mismo objeto que el de checks.mjs', () => {
  assert.equal(VOCABULARIO, VOCABULARIO_CHECKS, 'no puede haber una segunda copia del vocabulario')
})

test('el cargador no rechaza como desconocido ningun verbo del vocabulario de checks.mjs', () => {
  // si checks.mjs anade un verbo (file_matches) y el cargador no se entera, la
  // comprobacion sale "error" y la memoria deja de vigilarse de verdad
  for (const verbo of VOCABULARIO_CHECKS) {
    const { errors } = loadChecks(json({ m: { checks: [{ [verbo]: 'x' }] } }))
    assert.equal(
      /desconocid/.test(errors.join(' ')),
      false,
      `el cargador no conoce el verbo ${verbo}: ${errors.join(' ')}`,
    )
  }
})

test('una ruta que no es string no pasa la carga aunque la clave sea del vocabulario', () => {
  const { entries, errors } = loadChecks(json({ m: { checks: [{ file_exists: 42 }] } }))
  assert.ok(errors.length > 0, 'el valor tambien se valida, no solo la clave')
  assert.ok(entries.get('m').errors.length > 0)
  assert.deepEqual(entries.get('m').checks, [], 'no se ejecuta una comprobacion mal formada')
})

test('los valores mal formados de cada verbo se rechazan en la carga', () => {
  const malos = [
    { file_exists: '' },
    { file_absent: 'a/*/b.yml' },
    { file_contains: { path: 'a' } },
    { file_contains: { path: 'a', text: '' } },
    { file_contains: { path: 'a', text: 'b', extra: 1 } },
    { date_passed: 'manana' },
    { date_passed: '2026-9-1' },
  ]
  for (const check of malos) {
    const { entries } = loadChecks(json({ m: { checks: [check] } }))
    assert.ok(
      entries.get('m').errors.length > 0,
      `deberia fallar en la carga y no al ejecutarse: ${JSON.stringify(check)}`,
    )
  }
})

// --- claves duplicadas: JSON.parse aplica last-wins en silencio -----------

test('una memoria repetida en checks.json es error, no la ultima que gane', () => {
  const raw = '{"memories":{"m":{"checks":[{"file_exists":"a"}]},"m":{"checks":[{"file_exists":"b"}]}}}'
  // el escenario tiene que darse de verdad: al parsear ya solo queda una
  assert.equal(Object.keys(JSON.parse(raw).memories).length, 1)

  const { entries, errors, fatal } = loadChecks(raw)
  assert.equal(fatal, false)
  assert.match(errors.join(' '), /duplicada/)
  assert.ok(
    entries.get('m').errors.length > 0,
    'la memoria duplicada tiene que salir error: no se sabe cual de las dos vale',
  )
})

test('una clave repetida dentro de una entrada tambien es error de esa memoria', () => {
  const raw = '{"memories":{"m":{"checks":[{"file_exists":"a"}],"checks":[{"file_exists":"b"}]}}}'
  const { entries, errors } = loadChecks(raw)
  assert.match(errors.join(' '), /duplicada/)
  assert.ok(entries.get('m').errors.length > 0)
})

test('repetir "memories" es fatal: la mitad de las entradas desaparecio', () => {
  const raw = '{"memories":{"a":{"checks":[{"file_exists":"x"}]}},"memories":{"b":{"checks":[{"file_exists":"y"}]}}}'
  const r = loadChecks(raw)
  assert.equal(r.fatal, true, 'auditar con la mitad de las entradas perdidas seria un informe falso')
  assert.match(r.errors.join(' '), /duplicada/)
})

test('una clave de primer nivel repetida se reporta pero no impide cargar', () => {
  const raw = '{"_readme":["a"],"_readme":["b"],"memories":{"m":{"checks":[{"file_exists":"a"}]}}}'
  const r = loadChecks(raw)
  assert.equal(r.fatal, false)
  assert.match(r.errors.join(' '), /duplicada/)
  assert.equal(r.entries.size, 1)
})

test('dos claves iguales solo cuentan si estan en el mismo objeto', () => {
  const raw = '{"memories":{"a":{"checks":[{"file_exists":"x"}]},"b":{"checks":[{"file_exists":"x"}]}}}'
  const { errors } = loadChecks(raw)
  assert.deepEqual(errors, [], 'la misma clave en objetos distintos no es un duplicado')
})

test('el duplicado se detecta aunque venga escrito con escapes unicode', () => {
  // "m" y "m" son la misma clave para JSON.parse; compararlas sin
  // decodificar dejaria pasar el duplicado
  const raw = '{"memories":{"m":{"checks":[{"file_exists":"a"}]},"\\u006d":{"checks":[{"file_exists":"b"}]}}}'
  const { errors } = loadChecks(raw)
  assert.match(errors.join(' '), /duplicada/)
})

test('las llaves y comillas dentro de un string no fabrican duplicados falsos', () => {
  const raw = JSON.stringify({
    memories: {
      m: { revalidate: 'lleva {"m": 1} y una comilla \\" y una barra \\\\ dentro' },
      n: { revalidate: 'otra {"m": 2}' },
    },
  })
  const { errors, fatal } = loadChecks(raw)
  assert.equal(fatal, false)
  assert.deepEqual(errors, [])
})

test('un JSON demasiado anidado para recorrerlo es fatal, no un verde tranquilizador', () => {
  const raw = `{"memories":{"m":{"checks":${'['.repeat(400)}${']'.repeat(400)}}}}`
  const r = loadChecks(raw)
  assert.equal(r.fatal, true)
  assert.match(r.errors.join(' '), /duplicad/)
})

// --- comprobaciones tautologicas ------------------------------------------

test('una comprobacion que no puede fallar se rechaza al cargar', () => {
  const { entries, errors } = loadChecks(json({ project_x: { checks: [{ file_matches: '*' }] } }))
  assert.equal(errors.length, 1)
  assert.match(errors[0], /nunca puede fallar/)
  // la entrada sigue en el mapa con su error: su memoria sale "error", nunca
  // verde por una comprobacion que se declara vacua
  assert.equal(entries.get('project_x').errors.length, 1)
  assert.deepEqual(entries.get('project_x').checks, [])
})
