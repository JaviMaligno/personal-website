// scripts/memory-audit/checks.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, writeFileSync, mkdirSync, symlinkSync, realpathSync, readFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { resolveInRepo, matchGlob, runCheck, validateCheck, VOCABULARIO } from './checks.mjs'

const repo = () => {
  const dir = mkdtempSync(join(tmpdir(), 'memaudit-'))
  mkdirSync(join(dir, '.github', 'workflows'), { recursive: true })
  writeFileSync(join(dir, '.github', 'publish-schedule.json'), '{}')
  writeFileSync(join(dir, 'config.ts'), 'export const linkedinLinks = []')
  return dir
}

const ctx = (root) => ({ repoRoot: root, today: '2026-09-11' })

// En macOS el tmpdir es un enlace simbolico (/var -> /private/var), asi que el
// test tiene que resolver su propia raiz antes de comparar: resolveInRepo
// devuelve rutas REALES a proposito (es sobre esas sobre las que decide).
const raizReal = (root) => realpathSync(root)

/** Crea un FIFO, o devuelve null si el sistema no trae mkfifo. */
const creaFifo = (ruta) => {
  try {
    execFileSync('mkfifo', [ruta])
    return ruta
  } catch {
    return null
  }
}

test('resolveInRepo rechaza rutas que salen del repo', () => {
  const root = repo()
  assert.throws(() => resolveInRepo(root, '../../etc/passwd'), /fuera del repositorio/)
})

test('resolveInRepo acepta una ruta interna', () => {
  const root = repo()
  assert.equal(resolveInRepo(root, 'config.ts'), join(raizReal(root), 'config.ts'))
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

// --- 1. ReDoS en matchGlob -------------------------------------------------

test('matchGlob resuelve de inmediato un patron con 12 asteriscos que no casa', () => {
  // Con el RegExp concatenado sin anclaje esto no terminaba nunca.
  const pattern = '*'.repeat(12) + 'z.yml'
  const name = 'a'.repeat(40) + '.txt'
  const t0 = Date.now()
  assert.equal(matchGlob(pattern, name), false)
  assert.ok(Date.now() - t0 < 1000, `tardo ${Date.now() - t0} ms`)
})

test('matchGlob sigue casando con varios asteriscos cuando debe', () => {
  assert.equal(matchGlob('*-publish-*.yml', 'scheduled-publish-x.yml'), true)
  assert.equal(matchGlob('*', 'cualquier-cosa'), true)
  assert.equal(matchGlob('a*b*c', 'axxbyyc'), true)
  assert.equal(matchGlob('a*b*c', 'axxbyyd'), false)
})

test('el asterisco no cruza separadores de segmento', () => {
  assert.equal(matchGlob('*.yml', 'sub/dir.yml'), false)
})

// --- 2. Escape por enlace simbolico ---------------------------------------

test('resolveInRepo rechaza un symlink que apunta fuera del repo', () => {
  const root = repo()
  const fuera = mkdtempSync(join(tmpdir(), 'memaudit-fuera-'))
  writeFileSync(join(fuera, 'secreto.txt'), 'CLAVE-SECRETA')
  symlinkSync(fuera, join(root, 'escape'))
  assert.throws(() => resolveInRepo(root, 'escape/secreto.txt'), /fuera del repositorio/)
})

test('file_contains no es un oraculo de contenido a traves de un symlink', () => {
  const root = repo()
  const fuera = mkdtempSync(join(tmpdir(), 'memaudit-fuera-'))
  writeFileSync(join(fuera, 'secreto.txt'), 'CLAVE-SECRETA')
  symlinkSync(fuera, join(root, 'escape'))
  assert.throws(
    () => runCheck({ file_contains: { path: 'escape/secreto.txt', text: 'CLAVE' } }, ctx(root)),
    /fuera del repositorio/,
  )
})

test('resolveInRepo rechaza un objetivo inexistente bajo un symlink que sale del repo', () => {
  const root = repo()
  const fuera = mkdtempSync(join(tmpdir(), 'memaudit-fuera-'))
  symlinkSync(fuera, join(root, 'escape'))
  assert.throws(() => resolveInRepo(root, 'escape/todavia-no-existe.txt'), /fuera del repositorio/)
})

test('resolveInRepo sigue aceptando un fichero interno que aun no existe', () => {
  const root = repo()
  assert.equal(resolveInRepo(root, 'nuevo/fichero.txt'), join(raizReal(root), 'nuevo', 'fichero.txt'))
})

// --- 3. Falso verde en file_absent ----------------------------------------

test('file_absent avisa en el motivo de que el directorio no existe', () => {
  const root = repo()
  const r = runCheck({ file_absent: '.github/worklfows/scheduled-publish-*.yml' }, ctx(root))
  assert.equal(r.ok, true)
  assert.match(r.reason, /no existe/)
  assert.match(r.reason, /\.github\/worklfows/)
})

test('file_absent con asterisco en un segmento intermedio es error, no verde', () => {
  const root = repo()
  assert.throws(
    () => runCheck({ file_absent: '.github/*/scheduled-publish-x.yml' }, ctx(root)),
    /no soportado/,
  )
})

test('file_absent con directorio existente mantiene el motivo de siempre', () => {
  const root = repo()
  const r = runCheck({ file_absent: '.github/workflows/scheduled-publish-*.yml' }, ctx(root))
  assert.equal(r.ok, true)
  assert.doesNotMatch(r.reason, /directorio/)
})

// --- 4. Forma de file_contains --------------------------------------------

test('file_contains sin text es error, no rojo', () => {
  const root = repo()
  assert.throws(() => runCheck({ file_contains: { path: 'config.ts' } }, ctx(root)), /text/)
})

test('file_contains con text no string es error', () => {
  const root = repo()
  assert.throws(() => runCheck({ file_contains: { path: 'config.ts', text: 42 } }, ctx(root)), /text/)
})

test('file_contains sin path es error', () => {
  const root = repo()
  assert.throws(() => runCheck({ file_contains: { text: 'x' } }, ctx(root)), /path/)
})

test('file_contains con valor que no es objeto es error', () => {
  const root = repo()
  assert.throws(() => runCheck({ file_contains: 'config.ts' }, ctx(root)), /file_contains/)
})

// --- 5. Formato de date_passed --------------------------------------------

test('date_passed exige ISO estricto', () => {
  const root = repo()
  assert.throws(() => runCheck({ date_passed: 'manana' }, ctx(root)), /fecha/)
  assert.throws(() => runCheck({ date_passed: '2026-9-1' }, ctx(root)), /fecha/)
  assert.throws(() => runCheck({ date_passed: 20260901 }, ctx(root)), /fecha/)
})

test('date_passed rechaza una fecha con forma correcta pero imposible', () => {
  const root = repo()
  assert.throws(() => runCheck({ date_passed: '2026-02-30' }, ctx(root)), /fecha/)
})

// --- 6. La interrogacion es literal ---------------------------------------

test('la interrogacion no es un comodin en matchGlob', () => {
  assert.equal(matchGlob('a?.yml', 'a.yml'), false)
  assert.equal(matchGlob('a?.yml', 'ab.yml'), false)
  assert.equal(matchGlob('a?.yml', 'a?.yml'), true)
})

// --- 7. realpath fail-open: solo "no existe" justifica subir al padre -------

test('resolveInRepo no acepta una ruta con un bucle de enlaces simbolicos', () => {
  // ln -s b a; ln -s a b => realpath da ELOOP. Antes el catch ciego subia al
  // padre y recolgaba el nombre, con lo que la comprobacion de contencion se
  // saltaba entera: la ruta se daba por buena sin saber adonde apunta.
  const root = repo()
  symlinkSync(join(root, 'b'), join(root, 'a'))
  symlinkSync(join(root, 'a'), join(root, 'b'))
  assert.throws(() => resolveInRepo(root, 'a'), /ELOOP/)
})

test('un bucle de enlaces bajo el repo es error, no verde ni rojo', () => {
  const root = repo()
  symlinkSync(join(root, 'b'), join(root, 'a'))
  symlinkSync(join(root, 'a'), join(root, 'b'))
  assert.throws(() => runCheck({ file_exists: 'a' }, ctx(root)), /ELOOP/)
})

test('un bucle de enlaces en un ancestro tambien es error', () => {
  const root = repo()
  symlinkSync(join(root, 'b'), join(root, 'a'))
  symlinkSync(join(root, 'a'), join(root, 'b'))
  assert.throws(() => resolveInRepo(root, 'a/dentro/fichero.txt'), /ELOOP/)
})

test('ENOTDIR sobre un ancestro que es fichero sigue resolviendo dentro del repo', () => {
  // config.ts existe y es un fichero: "config.ts/sub" no existe, pero el padre
  // si resuelve, asi que la contencion se puede comprobar de verdad.
  const root = repo()
  assert.equal(resolveInRepo(root, 'config.ts/sub'), join(raizReal(root), 'config.ts', 'sub'))
})

// --- 8. file_contains con texto vacio --------------------------------------

test('file_contains con text vacio es error, no verde eterno', () => {
  // includes("") es siempre true: una comprobacion vacua se declararia verde
  // para siempre, que es justo el falso verde que el auditor debe evitar.
  const root = repo()
  assert.throws(() => runCheck({ file_contains: { path: 'config.ts', text: '' } }, ctx(root)), /text/)
})

test('file_contains con path vacio es error', () => {
  const root = repo()
  assert.throws(() => runCheck({ file_contains: { path: '', text: 'x' } }, ctx(root)), /path/)
})

// --- 9. validateCheck: la forma se valida en un unico sitio ----------------

test('validateCheck acepta las comprobaciones del vocabulario', () => {
  assert.deepEqual(validateCheck({ file_exists: 'config.ts' }).valido, true)
  assert.deepEqual(validateCheck({ file_matches: '.github/workflows/x-*.yml' }).valido, true)
  assert.deepEqual(validateCheck({ file_absent: '.github/workflows/x-*.yml' }).valido, true)
  assert.deepEqual(validateCheck({ file_contains: { path: 'config.ts', text: 'x' } }).valido, true)
  assert.deepEqual(validateCheck({ date_passed: '2026-09-01' }).valido, true)
})

test('validateCheck no toca el disco', () => {
  // Ruta inexistente y raiz inexistente: la forma es valida igualmente.
  const r = validateCheck({ file_exists: 'no/existe/en/ningun/sitio.txt' })
  assert.equal(r.valido, true)
  assert.equal(r.motivo, null)
})

test('validateCheck rechaza lo que no es un objeto de comprobacion', () => {
  for (const malo of [null, undefined, 'file_exists', 42, ['file_exists']]) {
    const r = validateCheck(malo)
    assert.equal(r.valido, false, `deberia rechazar ${JSON.stringify(malo)}`)
    assert.match(r.motivo, /objeto/)
  }
})

test('validateCheck rechaza un objeto sin claves', () => {
  const r = validateCheck({})
  assert.equal(r.valido, false)
  assert.match(r.motivo, /clave/)
})

test('validateCheck rechaza un objeto con mas de una clave', () => {
  const r = validateCheck({ file_exists: 'a.txt', date_passed: '2026-01-01' })
  assert.equal(r.valido, false)
  assert.match(r.motivo, /mas de una clave/)
})

test('validateCheck rechaza una clave fuera del vocabulario', () => {
  const r = validateCheck({ run_shell: 'rm -rf /' })
  assert.equal(r.valido, false)
  assert.match(r.motivo, /desconocida/)
})

test('validateCheck rechaza file_contains mal formado', () => {
  assert.match(validateCheck({ file_contains: 'config.ts' }).motivo, /file_contains/)
  assert.match(validateCheck({ file_contains: { text: 'x' } }).motivo, /path/)
  assert.match(validateCheck({ file_contains: { path: 'a.ts' } }).motivo, /text/)
  assert.match(validateCheck({ file_contains: { path: '', text: 'x' } }).motivo, /path/)
  assert.match(validateCheck({ file_contains: { path: 'a.ts', text: '' } }).motivo, /text/)
  assert.equal(validateCheck({ file_contains: { path: 'a.ts', text: 'x' } }).valido, true)
})

test('validateCheck rechaza fechas que no son ISO estricto o no existen', () => {
  for (const malo of ['manana', '2026-9-1', 20260901, '2026-02-30', '2026-13-01', '']) {
    const r = validateCheck({ date_passed: malo })
    assert.equal(r.valido, false, `deberia rechazar ${JSON.stringify(malo)}`)
    assert.match(r.motivo, /fecha/)
  }
})

test('validateCheck rechaza un asterisco en un segmento que no es el ultimo', () => {
  assert.match(validateCheck({ file_absent: '.github/*/x.yml' }).motivo, /no soportado/)
  assert.match(validateCheck({ file_matches: '*/x.yml' }).motivo, /no soportado/)
  assert.equal(validateCheck({ file_absent: '.github/workflows/x-*.yml' }).valido, true)
})

test('validateCheck rechaza rutas vacias', () => {
  assert.match(validateCheck({ file_exists: '' }).motivo, /file_exists/)
  assert.match(validateCheck({ file_absent: '' }).motivo, /file_absent/)
  assert.match(validateCheck({ file_exists: 42 }).motivo, /file_exists/)
})

// --- 10. file_exists con comodin: el falso rojo garantizado ----------------

test('file_exists rechaza cualquier comodin y remite a file_matches', () => {
  // Antes validateCheck los daba por buenos y runCheck los evaluaba con
  // existsSync literal: ningun fichero se llama "x-*.yml", asi que la
  // comprobacion salia ROJA siempre, en silencio.
  const root = repo()
  const r = validateCheck({ file_exists: '.github/workflows/scheduled-publish-*.yml' })
  assert.equal(r.valido, false)
  assert.match(r.motivo, /file_matches/)
  assert.throws(
    () => runCheck({ file_exists: '.github/workflows/scheduled-publish-*.yml' }, ctx(root)),
    /file_matches/,
  )
})

test('file_exists rechaza el comodin tambien en un segmento intermedio', () => {
  assert.equal(validateCheck({ file_exists: '.github/*/x.yml' }).valido, false)
})

test('file_exists sin comodin sigue funcionando', () => {
  const root = repo()
  assert.equal(runCheck({ file_exists: 'config.ts' }, ctx(root)).ok, true)
})

test('file_matches pasa cuando al menos un fichero casa', () => {
  const root = repo()
  writeFileSync(join(root, '.github', 'workflows', 'scheduled-publish-x.yml'), '')
  const r = runCheck({ file_matches: '.github/workflows/scheduled-publish-*.yml' }, ctx(root))
  assert.equal(r.ok, true)
  assert.match(r.reason, /scheduled-publish-\*\.yml/)
})

test('file_matches falla cuando no casa ninguno', () => {
  const root = repo()
  const r = runCheck({ file_matches: '.github/workflows/scheduled-publish-*.yml' }, ctx(root))
  assert.equal(r.ok, false)
})

test('file_matches avisa en el motivo de que el directorio no existe', () => {
  const root = repo()
  const r = runCheck({ file_matches: '.github/worklfows/x-*.yml' }, ctx(root))
  assert.equal(r.ok, false)
  assert.match(r.reason, /no existe/)
  assert.match(r.reason, /\.github\/worklfows/)
})

test('file_matches es el complemento exacto de file_absent', () => {
  const root = repo()
  const patron = '.github/workflows/scheduled-publish-*.yml'
  assert.equal(runCheck({ file_matches: patron }, ctx(root)).ok, false)
  assert.equal(runCheck({ file_absent: patron }, ctx(root)).ok, true)
  writeFileSync(join(root, '.github', 'workflows', 'scheduled-publish-x.yml'), '')
  assert.equal(runCheck({ file_matches: patron }, ctx(root)).ok, true)
  assert.equal(runCheck({ file_absent: patron }, ctx(root)).ok, false)
})

test('file_matches con asterisco en un segmento intermedio es error, no rojo', () => {
  const root = repo()
  assert.throws(() => runCheck({ file_matches: '.github/*/x.yml' }, ctx(root)), /no soportado/)
})

test('file_matches sin comodin se comporta como una existencia exacta', () => {
  const root = repo()
  assert.equal(runCheck({ file_matches: 'config.ts' }, ctx(root)).ok, true)
  assert.equal(runCheck({ file_matches: 'no-existe.ts' }, ctx(root)).ok, false)
})

test('file_matches rechaza rutas vacias o que no son string', () => {
  assert.match(validateCheck({ file_matches: '' }).motivo, /file_matches/)
  assert.match(validateCheck({ file_matches: 42 }).motivo, /file_matches/)
})

// --- 11. TOCTOU: se decide y se opera sobre la misma resolucion ------------

test('resolveInRepo devuelve la ruta REAL, no la logica', () => {
  // La contencion se decidia sobre rutaReal(target) pero se devolvia target:
  // existsSync/readFileSync/readdirSync volvian a seguir los enlaces, asi que
  // la decision de seguridad y la operacion miraban ficheros distintos.
  const root = repo()
  mkdirSync(join(root, 'real'))
  writeFileSync(join(root, 'real', 'f.txt'), 'contenido')
  symlinkSync(join(root, 'real'), join(root, 'enlace'))
  assert.equal(resolveInRepo(root, 'enlace/f.txt'), join(raizReal(root), 'real', 'f.txt'))
})

test('resolveInRepo resuelve tambien un enlace al propio fichero', () => {
  const root = repo()
  symlinkSync(join(root, 'config.ts'), join(root, 'alias.ts'))
  assert.equal(resolveInRepo(root, 'alias.ts'), join(raizReal(root), 'config.ts'))
})

// --- 12. Ficheros que no son ficheros: un FIFO cuelga el proceso -----------

test('file_contains sobre un FIFO es error, no un cuelgue', { timeout: 10000 }, (t) => {
  const root = repo()
  if (!creaFifo(join(root, 'tuberia'))) return t.skip('sin mkfifo en este sistema')
  // readFileSync sobre un FIFO sin escritor bloquea para siempre, y un cuelgue
  // no lo atrapa ningun try/catch: hay que mirar el tipo ANTES de abrir.
  assert.throws(
    () => runCheck({ file_contains: { path: 'tuberia', text: 'x' } }, ctx(root)),
    /regular/,
  )
})

test('file_absent con un FIFO por directorio es error', { timeout: 10000 }, (t) => {
  const root = repo()
  if (!creaFifo(join(root, 'tuberia'))) return t.skip('sin mkfifo en este sistema')
  assert.throws(() => runCheck({ file_absent: 'tuberia/x-*.yml' }, ctx(root)), /directorio/)
})

test('file_contains sobre un directorio es error, no rojo', () => {
  const root = repo()
  assert.throws(
    () => runCheck({ file_contains: { path: '.github', text: 'x' } }, ctx(root)),
    /regular/,
  )
})

test('file_matches con un fichero regular por directorio es error', () => {
  const root = repo()
  assert.throws(() => runCheck({ file_matches: 'config.ts/x-*.yml' }, ctx(root)), /directorio/)
})

// --- 13. date_passed: no ha empezado a ser cierto, no ha dejado de serlo ---

test('date_passed no acusa de obsolescencia a una fecha futura', () => {
  const root = repo()
  const r = runCheck({ date_passed: '2026-12-01' }, ctx(root))
  assert.equal(r.ok, false)
  // El informe define rojo como "afirma algo que ya no es cierto". Una fecha
  // que aun no ha llegado no ha caducado: todavia no ha empezado a ser cierta.
  assert.doesNotMatch(r.reason, /ya no/)
  assert.match(r.reason, /todavia no/)
})

test('date_passed sigue pasando con una fecha ya vencida y con la de hoy', () => {
  const root = repo()
  assert.equal(runCheck({ date_passed: '2026-09-01' }, ctx(root)).ok, true)
  assert.equal(runCheck({ date_passed: '2026-09-11' }, ctx(root)).ok, true)
})

// --- 14. VOCABULARIO exportado: un unico sitio donde vive la lista ---------

test('VOCABULARIO se exporta con los verbos que entiende runCheck', () => {
  assert.ok(Array.isArray(VOCABULARIO))
  assert.deepEqual(
    [...VOCABULARIO].sort(),
    ['date_passed', 'file_absent', 'file_contains', 'file_exists', 'file_matches'],
  )
})

test('VOCABULARIO no se puede mutar desde fuera', () => {
  assert.ok(Object.isFrozen(VOCABULARIO))
})

test('todo verbo de VOCABULARIO lo acepta validateCheck con un valor valido', () => {
  const ejemplos = {
    file_exists: 'config.ts',
    file_matches: 'dir/x-*.yml',
    file_absent: 'dir/x-*.yml',
    file_contains: { path: 'config.ts', text: 'x' },
    date_passed: '2026-01-01',
  }
  for (const verbo of VOCABULARIO) {
    assert.equal(validateCheck({ [verbo]: ejemplos[verbo] }).valido, true, `falla ${verbo}`)
  }
})

test('file_contains.path tampoco admite comodines', () => {
  // Misma trampa que file_exists: readFileSync compara el "*" literalmente,
  // asi que la comprobacion saldria roja siempre.
  const root = repo()
  const r = validateCheck({ file_contains: { path: 'dir/x-*.yml', text: 'x' } })
  assert.equal(r.valido, false)
  assert.match(r.motivo, /comodines/)
  assert.throws(
    () => runCheck({ file_contains: { path: 'dir/x-*.yml', text: 'x' } }, ctx(root)),
    /comodines/,
  )
})

// --- 9. Comprobaciones tautologicas ---------------------------------------
// El _readme de checks.json lo dice: una comprobacion que siempre pasa es PEOR
// que ninguna, porque da confianza falsa. {"file_matches": "*"} sale verde
// siempre (el dirname es "." y la raiz del repo nunca esta vacia), asi que no
// vigila nada: se rechaza en la forma, y su memoria acaba en "error".

test('validateCheck rechaza un file_matches que no puede fallar', () => {
  for (const patron of ['*', '**', '***', 'dir/*', '.github/workflows/*', 'a/b/**']) {
    const { valido, motivo } = validateCheck({ file_matches: patron })
    assert.equal(valido, false, `tendria que rechazarse: ${patron}`)
    assert.match(motivo, /nunca puede fallar/, patron)
  }
})

test('validateCheck da el mismo trato a un file_absent tautologico', () => {
  for (const patron of ['*', '**', 'dir/*']) {
    const { valido, motivo } = validateCheck({ file_absent: patron })
    assert.equal(valido, false, `tendria que rechazarse: ${patron}`)
    assert.match(motivo, /nunca puede fallar/, patron)
  }
})

test('un file_matches tautologico es error en runCheck, nunca verde', () => {
  const root = repo()
  assert.throws(() => runCheck({ file_matches: '*' }, ctx(root)), /nunca puede fallar/)
})

test('un file_absent tautologico tambien es error', () => {
  const root = repo()
  assert.throws(() => runCheck({ file_absent: '.github/workflows/*' }, ctx(root)), /nunca puede fallar/)
})

test('un patron con parte literal sigue valiendo', () => {
  for (const patron of ['*.yml', 'a*', '.github/workflows/*.yml', 'dir/x*y', '*-publish-*.yml']) {
    assert.equal(validateCheck({ file_matches: patron }).valido, true, patron)
    assert.equal(validateCheck({ file_absent: patron }).valido, true, patron)
  }
})

// --- 10. Caja: los cuatro verbos tienen que coincidir ----------------------
// file_exists y file_contains delegaban en existsSync/readFileSync, que en
// APFS no distinguen mayusculas, mientras file_matches y file_absent comparan
// con matchGlob, que si. La misma ruta recibia veredictos distintos segun el
// verbo, y ademas el veredicto dependia del sistema de ficheros.

test('file_exists distingue mayusculas aunque el sistema de ficheros no', () => {
  const root = repo()
  assert.equal(runCheck({ file_exists: 'config.ts' }, ctx(root)).ok, true)
  assert.equal(runCheck({ file_exists: 'Config.ts' }, ctx(root)).ok, false)
  assert.equal(runCheck({ file_exists: 'CONFIG.TS' }, ctx(root)).ok, false)
})

test('file_contains distingue mayusculas en la ruta', () => {
  const root = repo()
  const bien = runCheck({ file_contains: { path: 'config.ts', text: 'linkedinLinks' } }, ctx(root))
  assert.equal(bien.ok, true)
  const mal = runCheck({ file_contains: { path: 'CONFIG.TS', text: 'linkedinLinks' } }, ctx(root))
  assert.equal(mal.ok, false)
  assert.match(mal.reason, /no existe/)
})

test('los cuatro verbos dan el mismo veredicto sobre la misma ruta', () => {
  const root = repo()
  // con la caja escrita tal cual esta en el disco: el fichero esta
  assert.equal(runCheck({ file_exists: 'config.ts' }, ctx(root)).ok, true)
  assert.equal(runCheck({ file_matches: 'config.t*' }, ctx(root)).ok, true)
  assert.equal(runCheck({ file_absent: 'config.t*' }, ctx(root)).ok, false)
  assert.equal(runCheck({ file_contains: { path: 'config.ts', text: 'export' } }, ctx(root)).ok, true)
  // con otra caja: para los cuatro, ese fichero no esta
  assert.equal(runCheck({ file_exists: 'CONFIG.TS' }, ctx(root)).ok, false)
  assert.equal(runCheck({ file_matches: 'CONFIG.T*' }, ctx(root)).ok, false)
  assert.equal(runCheck({ file_absent: 'CONFIG.T*' }, ctx(root)).ok, true)
  assert.equal(runCheck({ file_contains: { path: 'CONFIG.TS', text: 'export' } }, ctx(root)).ok, false)
})

test('un directorio ancestro escrito con otra caja tampoco cuela', () => {
  const root = repo()
  assert.equal(runCheck({ file_exists: '.github/publish-schedule.json' }, ctx(root)).ok, true)
  assert.equal(runCheck({ file_exists: '.GitHub/publish-schedule.json' }, ctx(root)).ok, false)
  assert.equal(runCheck({ file_matches: '.GitHub/publish-schedule*.json' }, ctx(root)).ok, false)
  assert.equal(
    runCheck({ file_contains: { path: '.GitHub/publish-schedule.json', text: '{' } }, ctx(root)).ok,
    false,
  )
})

test('la comprobacion de caja no convierte un enlace roto en verde', () => {
  // el listado del directorio si trae el nombre del enlace: la existencia la
  // sigue decidiendo existsSync, que no la da por buena si el destino no esta
  const root = repo()
  symlinkSync(join(root, 'destino-que-no-existe'), join(root, 'roto'))
  assert.equal(runCheck({ file_exists: 'roto' }, ctx(root)).ok, false)
})

test('la caja se comprueba sin inventarse un veredicto cuando un ancestro es fichero', () => {
  // config.ts es un fichero: "config.ts/sub" no existe y eso es rojo, no error
  const root = repo()
  assert.equal(runCheck({ file_exists: 'config.ts/sub' }, ctx(root)).ok, false)
})

test('el modulo declara por escrito su semantica de mayusculas', () => {
  // es una decision, no un accidente del sistema de ficheros: tiene que estar
  // dicha donde la lea quien escriba una comprobacion
  const fuente = readFileSync(new URL('./checks.mjs', import.meta.url), 'utf8')
  const cabecera = fuente.slice(0, fuente.indexOf('import '))
  assert.match(cabecera, /mayuscul/i)
})

// --- 15. Espacios al principio o al final del patron -----------------------
// "* " esquivaba la deteccion de tautologia: no es "solo comodines" caracter a
// caracter, pero como patron no puede fallar nunca, asi que file_absent con ese
// valor salia verde para siempre.

test('un patron con espacio al final se rechaza', () => {
  const r = validateCheck({ file_absent: '* ' })
  assert.equal(r.valido, false)
  assert.match(r.motivo, /espacios al principio o al final/)
})

test('un patron con espacio al principio se rechaza', () => {
  assert.equal(validateCheck({ file_matches: ' scripts/*.mjs' }).valido, false)
})

test('un patron con espacio interior sigue siendo valido', () => {
  // Un nombre de fichero puede llevar espacios dentro; lo sospechoso son los
  // extremos, que ademas esquivaban la comprobacion de tautologia.
  assert.equal(validateCheck({ file_exists: 'docs/con espacio.md' }).valido, true)
})
