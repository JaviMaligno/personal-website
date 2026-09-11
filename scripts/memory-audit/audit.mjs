// scripts/memory-audit/audit.mjs
// Clasifica cada memoria en verde / rojo / gris / error.
// Ver el plan en docs/superpowers/plans/2026-09-11-auditoria-vigencia-memorias.md
//
// El auditor NO LEE NUNCA el contenido de una memoria: solo recibe la lista de
// NOMBRES del directorio de memorias y busca sus comprobaciones en checks.json,
// que vive en este repositorio. Las memorias son privadas y el repositorio es
// publico, asi que esto es a la vez una decision de diseno y una garantia de
// privacidad: por aqui no puede escaparse el cuerpo de una memoria.

import { existsSync, realpathSync, statSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

import { runCheck } from './checks.mjs'

/**
 * Motivo por el que `ruta` no sirve como raiz del repositorio, o null si sirve.
 *
 * Toda comprobacion del vocabulario resuelve rutas RELATIVAS contra esta raiz.
 * Con una raiz equivocada fallan todas a la vez y el auditor declara obsoletas
 * todas las memorias con total seguridad, en vez de admitir que no puede
 * comprobar nada: un fallo masivo, seguro de si mismo y en la direccion que
 * infla el dato. Por eso se exige que la raiz exista, sea un directorio y
 * ademas PAREZCA la raiz de un repositorio (que contenga .git).
 *
 * A proposito no hay heuristica mas lista (buscar .git hacia arriba, adivinar
 * la raiz desde la ruta del script): eso convertiria una invocacion equivocada
 * en una auditoria contra otro sitio. Fallar pronto y en voz alta es lo que se
 * quiere. `.git` vale como directorio y como fichero: en un worktree y en un
 * submodulo es un fichero "gitdir: ...", y esa sigue siendo una raiz de verdad.
 */
export function motivoRaizInvalida(ruta) {
  if (typeof ruta !== 'string' || ruta === '') {
    return 'no es una ruta'
  }
  let st
  try {
    st = statSync(ruta)
  } catch (err) {
    const codigo = (err && err.code) || (err && err.message)
    return codigo === 'ENOENT' ? 'no existe' : `no se puede leer (${codigo})`
  }
  if (!st.isDirectory()) {
    return 'no es un directorio'
  }
  if (!existsSync(join(ruta, '.git'))) {
    return 'no parece la raiz de un repositorio: no contiene .git'
  }
  return null
}

/**
 * Sube desde `desde` buscando la raiz del repositorio que lo contiene.
 * Devuelve la ruta o null si no hay ninguna.
 *
 * Se usa para deducir la raiz por defecto a partir de donde vive checks.json,
 * porque las rutas de sus comprobaciones son relativas a ESE repositorio. La
 * alternativa —el directorio actual— daba un informe falso en silencio al
 * lanzar el CLI desde otro repositorio: como tambien tiene su .git, pasaba la
 * validacion y cada ruta se resolvia contra el arbol equivocado.
 */
export function raizDeRepositorio(desde) {
  if (typeof desde !== 'string' || desde === '') return null
  let actual = resolve(desde)
  for (;;) {
    if (existsSync(join(actual, '.git'))) return actual
    const padre = dirname(actual)
    if (padre === actual) return null
    actual = padre
  }
}

/**
 * Clasifica una memoria a partir de su entrada de checks.json.
 * `run` es inyectable para poder probar la clasificacion sin tocar disco.
 *
 * `revalidate` se propaga tal cual: es una pregunta para una persona, no una
 * comprobacion, asi que no influye en el estado (una memoria que solo tiene
 * pregunta sigue siendo gris) pero si tiene que llegar al informe.
 */
export function classify(entry, ctx, run = runCheck) {
  const name = entry.name
  const revalidate = entry.revalidate ?? null
  const errores = Array.isArray(entry.errors) ? [...entry.errors] : []

  // entrada invalida: no se ejecuta nada. Media entrada ejecutada daria un
  // veredicto basado en la mitad que si se entendio.
  if (errores.length > 0) return { name, state: 'error', failures: errores, revalidate }

  const checks = Array.isArray(entry.checks) ? entry.checks : []
  if (checks.length === 0) return { name, state: 'gris', failures: [], revalidate }

  const fallos = []
  for (const check of checks) {
    try {
      const resultado = run(check, ctx)
      if (typeof resultado !== 'object' || resultado === null || typeof resultado.ok !== 'boolean') {
        errores.push(`la comprobacion no devolvio un resultado utilizable: ${JSON.stringify(Object.keys(check))}`)
        continue
      }
      if (!resultado.ok) fallos.push(resultado.reason)
    } catch (err) {
      errores.push(err.message)
    }
  }

  // Si algo no se pudo evaluar, el veredicto es "error" aunque otra
  // comprobacion haya fallado: con una sola comprobacion ciega ya no se puede
  // afirmar ni que la memoria esta viva ni que esta muerta.
  if (errores.length > 0) return { name, state: 'error', failures: errores, revalidate }
  return { name, state: fallos.length > 0 ? 'rojo' : 'verde', failures: fallos, revalidate }
}

/**
 * La clave de checks.json que corresponde a un fichero de memoria.
 *
 * La extension se compara en minusculas: el sistema de ficheros de macOS no
 * distingue mayusculas, asi que "memoria.MD" y "memoria.md" son el mismo
 * fichero y tienen que buscar la misma clave. Comparandola tal cual, una
 * memoria escrita ".MD" buscaba la clave "memoria.MD", no la encontraba y
 * salia gris con su comprobacion colgando de huerfana.
 */
function claveDeMemoria(nombreFichero) {
  return esExtensionMarkdown(nombreFichero) ? nombreFichero.slice(0, -3) : nombreFichero
}

/** True si el nombre acaba en ".md" en cualquier caja. */
function esExtensionMarkdown(nombre) {
  return nombre.toLowerCase().endsWith('.md')
}

// El indice del directorio de memorias: no es una memoria y no se audita.
const INDICE = 'memory.md'

/**
 * True si el fichero del directorio de memorias hay que auditarlo.
 *
 * Todo se compara en minusculas. El filtro era sensible a mayusculas sobre un
 * sistema de ficheros que no lo es: "memoria.MD" no se auditaba, no contaba en
 * el total y desaparecia del informe sin decir nada, que es justo la forma de
 * fallar que esta herramienta tiene prohibida.
 */
export function esFicheroDeMemoria(nombre) {
  if (typeof nombre !== 'string') return false
  const minusculas = nombre.toLowerCase()
  return minusculas.endsWith('.md') && minusculas !== INDICE
}

/**
 * Audita una lista de NOMBRES de memoria contra las entradas de checks.json.
 *
 * Devuelve {results, orphans}. `orphans` son las claves de checks.json que no
 * corresponden a ninguna memoria del directorio: es el riesgo conocido de
 * separar las comprobaciones de la memoria (basta renombrar una memoria para
 * dejarlas colgando y que la memoria pase a gris sin que nadie lo note), asi
 * que se reportan en vez de callarlas.
 */
export function auditMemories({ memoryNames, entries, ctx, run = runCheck }) {
  if (!Array.isArray(memoryNames)) {
    throw new TypeError('memoryNames tiene que ser un array de nombres de fichero')
  }
  const mapa = entries instanceof Map ? entries : new Map(Object.entries(entries ?? {}))

  const usadas = new Set()
  const results = []
  // ordenado para que dos pasadas con el mismo estado den el mismo informe
  for (const nombre of [...memoryNames].sort()) {
    const clave = claveDeMemoria(nombre)
    const entrada = mapa.get(clave)
    if (entrada === undefined) {
      // sin comprobacion declarada: gris. Es el estado correcto para las
      // preferencias y los criterios, que no son comprobables desde un repo.
      results.push({ name: nombre, state: 'gris', failures: [], revalidate: null })
      continue
    }
    usadas.add(clave)
    results.push(classify({ ...entrada, name: nombre }, ctx, run))
  }

  const orphans = [...mapa.keys()].filter((clave) => !usadas.has(clave)).sort()
  return { results, orphans }
}

export function summarise(results) {
  const s = { verde: 0, rojo: 0, gris: 0, error: 0, total: results.length }
  for (const r of results) s[r.state] += 1
  return s
}

/**
 * Fecha de HOY en el calendario local, AAAA-MM-DD.
 *
 * No vale toISOString(): eso es UTC, y las fechas de date_passed las escribe
 * una persona mirando su calendario. En UTC+2 hay una ventana de 00:00 a 02:00
 * en la que UTC va todavia por ayer, y una fecha ya vencida se reportaria como
 * "aun no ha llegado": un falso rojo que ademas solo aparece de madrugada.
 */
export function fechaLocalISO(fecha = new Date()) {
  const dosDigitos = (n) => String(n).padStart(2, '0')
  return `${fecha.getFullYear()}-${dosDigitos(fecha.getMonth() + 1)}-${dosDigitos(fecha.getDate())}`
}

const MAX_INTERPOLADO = 200

// Tope de motivos por memoria en el informe. Una entrada con miles de
// comprobaciones malformadas generaba un informe imposible de leer, que es una
// forma barata de esconder las demas memorias rojas.
const MAX_MOTIVOS = 20

/**
 * Aplana un valor que viene de fuera para poder interpolarlo en el informe.
 * Nombres de fichero y claves de checks.json son entrada hostil: un nombre
 * POSIX puede llevar saltos de linea, y sin esto se podrian fabricar secciones
 * o contadores falsos dentro del informe, o colar instrucciones dirigidas a
 * quien lo lea. Resultado: una sola linea, sin caracteres de control, recortada.
 */
export function sanitizeValue(value, maxLength = MAX_INTERPOLADO) {
  const text = typeof value === 'string' ? value : String(value ?? '')
  const flat = text
    // todo lo que Unicode trata como salto de linea obligatorio -> simbolo
    // visible, para que se vea que lo habia. U+0085 (NEL) cuenta: es un control
    // C1 y parte lineas en terminales y editores.
    .replace(/\r\n|[\n\r\u0085\u2028\u2029]/g, '\u23CE')
    // el resto de controles: C0, DEL y los 32 C1 (escapes ANSI incluidos)
    .replace(/[\u0000-\u001f\u007f-\u009f]/g, '\u00B7')
  return flat.length > maxLength ? `${flat.slice(0, maxLength)}…` : flat
}

/** Los motivos que caben en el informe, y cuantos se quedaron fuera. */
function motivosLimitados(failures) {
  const lista = Array.isArray(failures) ? failures : []
  return { mostrados: lista.slice(0, MAX_MOTIVOS), omitidos: Math.max(0, lista.length - MAX_MOTIVOS) }
}

/** Escribe los motivos de una memoria, con el tope y diciendo que omitio. */
function lineasDeMotivos(lines, failures) {
  const { mostrados, omitidos } = motivosLimitados(failures)
  for (const f of mostrados) lines.push(`    ${sanitizeValue(f)}`)
  if (omitidos > 0) {
    lines.push(`    (y ${omitidos} motivos mas, omitidos: el tope del informe es ${MAX_MOTIVOS} por memoria)`)
  }
}

/**
 * Informe en texto. Solo nombres, estados y motivos: nunca el cuerpo de una
 * memoria, que este programa ni siquiera llega a leer.
 */
export function formatReport(results, summary, { orphans = [], issues = [] } = {}) {
  const lines = []
  lines.push('# Auditoria de vigencia de memorias')
  lines.push('')
  lines.push(`total: ${summary.total}`)
  lines.push(`verde: ${summary.verde}   (la comprobacion pasa)`)
  lines.push(`rojo: ${summary.rojo}   (afirma algo que ya no es cierto)`)
  lines.push(`gris: ${summary.gris}   (no admite comprobacion)`)
  lines.push(`error: ${summary.error}   (comprobacion ilegible o no evaluable)`)
  lines.push(`huerfanos: ${orphans.length}   (comprobaciones sin memoria)`)
  lines.push('')

  const rojas = results.filter((r) => r.state === 'rojo')
  if (rojas.length > 0) {
    lines.push('## Rojas')
    for (const r of rojas) {
      lines.push(`- ${sanitizeValue(r.name)}`)
      lineasDeMotivos(lines, r.failures)
    }
    lines.push('')
  }

  const errores = results.filter((r) => r.state === 'error')
  if (errores.length > 0) {
    lines.push('## Errores')
    lines.push('(no se puede saber si siguen siendo ciertas: ni verde ni rojo)')
    for (const r of errores) {
      lines.push(`- ${sanitizeValue(r.name)}`)
      lineasDeMotivos(lines, r.failures)
    }
    lines.push('')
  }

  // Una comprobacion huerfana no vigila nada. Si esto no saliera, un renombrado
  // de memoria convertiria su comprobacion en decorado y la memoria en gris.
  if (orphans.length > 0) {
    lines.push('## Huerfanos')
    lines.push('(claves de checks.json sin memoria: renombrela o borre la entrada)')
    for (const clave of orphans) lines.push(`- ${sanitizeValue(clave)}`)
    lines.push('')
  }

  if (issues.length > 0) {
    lines.push('## Problemas de checks.json')
    for (const i of issues) lines.push(`- ${sanitizeValue(i)}`)
    lines.push('')
  }

  // La pregunta de revalidacion no se evalua (no es comprobable desde aqui),
  // pero se reporta: si no saliera en ningun sitio, la mitad de "se reporta y
  // no se evalua" quedaria sin cumplir.
  const revalidables = results.filter((r) => r.revalidate)
  if (revalidables.length > 0) {
    lines.push('## Revalidacion manual')
    lines.push('(preguntas para una persona; estas memorias siguen contando como grises)')
    for (const r of revalidables) {
      lines.push(`- ${sanitizeValue(r.name)}: ${sanitizeValue(r.revalidate)}`)
    }
    lines.push('')
  }

  return lines.join('\n')
}

/**
 * Dice si este fichero se ha invocado como programa (y no importado como modulo).
 * Segunda pasada por realpath porque Node resuelve el modulo a su ruta real:
 * invocarlo por un enlace simbolico (en macOS /var/... lo es) daria false y el
 * CLI no correria. Nunca da falso positivo: solo casa el mismo fichero.
 */
function esInvocacionDirecta() {
  const invocado = process.argv[1]
  if (!invocado) return false
  if (import.meta.url === pathToFileURL(invocado).href) return true
  try {
    return import.meta.url === pathToFileURL(realpathSync(invocado)).href
  } catch {
    return false
  }
}

// --- CLI ---------------------------------------------------------------
// node scripts/memory-audit/audit.mjs --memory-dir <ruta> [--repo-root <ruta>]
//                                     [--checks <ruta a checks.json>]
//
// Codigos de salida (para poder encadenarlo en un hook o en CI):
//   0  ninguna memoria roja ni con error, ninguna comprobacion huerfana y
//      ningun problema de checks.json
//   1  al menos una de estas cuatro cosas:
//        - una memoria roja (afirma algo que ya no es cierto),
//        - una memoria con error (no se puede saber si sigue siendo cierta),
//        - una comprobacion huerfana: su memoria se renombro o se borro, asi
//          que no vigila nada y su memoria cayo a gris sin que nadie lo note.
//          Es la decadencia silenciosa que esta herramienta existe para
//          detectar, asi que cuenta como problema y no como un 0,
//        - un problema de checks.json que deja alguna comprobacion sin aplicar.
//   2  error de invocacion: falta un argumento, la raiz del repositorio no
//      existe / no es un directorio / no parece una raiz (no contiene .git),
//      o el directorio de memorias o el fichero de comprobaciones no se pueden
//      usar. Con 2 no se imprime informe: un informe contra una raiz
//      equivocada seria toda la auditoria en rojo y con total seguridad.
//
// El guard compara con pathToFileURL, no con 'file://' + argv[1]: import.meta.url
// va percent-encoded, asi que concatenar la ruta en crudo hace false la comparacion
// en cuanto la ruta lleva un espacio o un acento, y el CLI saldria con 0 sin
// imprimir nada. Un fallo silencioso es lo peor que puede hacer una auditoria.
if (esInvocacionDirecta()) {
  const { readdirSync, readFileSync } = await import('node:fs')
  const { fileURLToPath } = await import('node:url')
  const { loadChecks } = await import('./load-checks.mjs')

  const arg = (name, fallback) => {
    const i = process.argv.indexOf(name)
    if (i === -1) return fallback
    const valor = process.argv[i + 1]
    if (valor === undefined || valor.startsWith('--')) {
      console.error(`falta el valor de ${name}`)
      process.exit(2)
    }
    return valor
  }

  const memoryDir = arg('--memory-dir')
  if (!memoryDir) {
    console.error('falta --memory-dir')
    process.exit(2)
  }
  const checksPath = arg('--checks', join(dirname(fileURLToPath(import.meta.url)), 'checks.json'))
  const today = fechaLocalISO()

  let rawChecks
  try {
    rawChecks = readFileSync(checksPath, 'utf8')
  } catch (err) {
    console.error(`no se pudo leer el fichero de comprobaciones ${checksPath}: ${err.message}`)
    process.exit(2)
  }

  const { entries, errors, fatal } = loadChecks(rawChecks)
  if (fatal) {
    // sin comprobaciones cargadas TODA la auditoria saldria gris, que es un
    // informe tranquilizador y falso: mejor no dar informe ninguno
    console.error(`fichero de comprobaciones inservible: ${errors.join('; ')}`)
    process.exit(2)
  }

  // La raiz por defecto sale del fichero de comprobaciones, NO del directorio
  // actual. Las rutas de checks.json son relativas al repositorio que lo
  // contiene, asi que derivarla del cwd hacia que lanzar el CLI desde otro
  // repositorio —que tiene su propio .git y por tanto pasaba la validacion—
  // resolviese cada ruta contra el arbol equivocado: una tanda de rojos falsos
  // con total seguridad. Un --repo-root explicito sigue mandando.
  const repoRootPasado = process.argv.includes('--repo-root')
  const repoRootDeducida = raizDeRepositorio(dirname(checksPath))
  if (!repoRootPasado && repoRootDeducida === null) {
    // Nunca caer al directorio actual en silencio: como cualquier repositorio
    // tiene su .git, pasaria la validacion de mas abajo y la auditoria se
    // resolveria contra un arbol que no es el suyo, dando rojos falsos con
    // total seguridad. Si no se puede deducir, se pide explicitamente.
    console.error(
      `no se puede deducir la raiz del repositorio a partir de ${checksPath}: ` +
        'ese fichero no esta dentro de ningun repositorio. Pase --repo-root con la raiz ' +
        'contra la que deben resolverse las rutas de las comprobaciones.',
    )
    process.exit(2)
  }
  const repoRoot = arg('--repo-root', repoRootDeducida)
  const motivoRaiz = motivoRaizInvalida(repoRoot)
  if (motivoRaiz) {
    const origen = repoRootPasado ? '--repo-root' : '--repo-root (deducido de checks.json, por defecto)'
    console.error(
      `${origen} no sirve como raiz del repositorio: ${repoRoot}: ${motivoRaiz}. ` +
        'Todas las comprobaciones resuelven sus rutas contra esa raiz, asi que con una ' +
        'equivocada saldrian todas rojas a la vez y el informe seria falso.',
    )
    process.exit(2)
  }

  let nombres
  try {
    // solo los NOMBRES: aqui no se abre ninguna memoria
    nombres = readdirSync(memoryDir)
  } catch (err) {
    // mismo trato que la falta del argumento: es un error del usuario, no un fallo
    console.error(`no se pudo leer el directorio de memorias ${memoryDir}: ${err.message}`)
    process.exit(2)
  }

  // MEMORY.md es el indice, no una memoria
  const memoryNames = nombres.filter(esFicheroDeMemoria)
  const { results, orphans } = auditMemories({ memoryNames, entries, ctx: { repoRoot, today } })

  const summary = summarise(results)
  console.log(formatReport(results, summary, { orphans, issues: errors }))
  const hayProblema =
    summary.rojo > 0 || summary.error > 0 || errors.length > 0 || orphans.length > 0
  process.exit(hayProblema ? 1 : 0)
}
