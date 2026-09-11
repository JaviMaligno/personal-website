// scripts/memory-audit/checks.mjs
// Vocabulario cerrado de comprobaciones de vigencia.
//
// Lo interpreta este modulo; NUNCA se ejecuta shell. Las comprobaciones viven
// en scripts/memory-audit/checks.json, dentro del repositorio, y este modulo
// no lee jamas el contenido de una memoria.
// Ver docs/superpowers/specs/2026-09-11-dos-regimenes-de-memoria-design.md
//
// MAYUSCULAS Y MINUSCULAS: los cuatro verbos comparan las rutas DISTINGUIENDO
// la caja, tambien sobre un sistema de ficheros que no la distingue (APFS de
// macOS, NTFS). Es una decision, no un accidente: existsSync y readFileSync
// son insensibles ahi, mientras matchGlob compara caracter a caracter y si es
// sensible, asi que la misma ruta recibia veredictos distintos segun el verbo
// y el mismo checks.json daba resultados distintos en macOS y en el Linux de
// CI. Para no adivinar, la caja se comprueba mirando el nombre REAL de cada
// entrada en el listado de su directorio: "Config.ts" no casa con el fichero
// "config.ts" en ningun sistema. Una ruta escrita con otra caja es un "no
// existe" (rojo), no un error: el listado del directorio dice sin ambiguedad
// que esa entrada no esta.
//
// En este modulo no se construye ningun RegExp, ni siquiera literal: toda la
// comparacion de formas (fecha ISO, separadores de ruta, glob) es un recorrido
// de caracteres. Asi la clase entera de fallos "regex sobre entrada ajena"
// (ReDoS, metacaracteres interpretados) no puede reaparecer con un parche.
//
// Que afirma cada verbo (el informe traduce "pasa" a verde y "no pasa" a rojo,
// asi que el verbo tiene que afirmar algo que pueda dejar de ser cierto):
//   file_exists    esta ruta EXACTA existe. No admite comodines: para eso esta
//                  file_matches. Con "*" existsSync busca un fichero llamado
//                  literalmente "x-*.yml" y siempre falla: rojo garantizado.
//   file_matches   existe AL MENOS UN fichero que casa con el patron.
//   file_absent    NO existe ninguno que case. Complemento exacto del anterior.
//   file_contains  este fichero sigue conteniendo este texto.
//   date_passed    "esta fecha ya paso". Sirve para caducar una memoria en una
//                  fecha conocida (un contrato, una migracion con plazo). Si la
//                  fecha aun no ha llegado la afirmacion no ha caducado: es que
//                  TODAVIA no es cierta. El vocabulario solo sabe decir pasa o
//                  no pasa, asi que el motivo lo dice con esas palabras y no
//                  acusa de obsolescencia a algo que no ha ocurrido aun.

import { existsSync, readFileSync, readdirSync, realpathSync, lstatSync } from 'node:fs'
import { resolve, sep, dirname, basename, join, relative } from 'node:path'

/**
 * Claves del vocabulario. Cualquier otra cosa es un error, no una extension.
 * Se exporta para que load-checks.mjs no duplique la lista: dos copias que se
 * desincronizan producen entradas que un lado acepta y el otro no entiende.
 */
export const VOCABULARIO = Object.freeze([
  'file_exists',
  'file_matches',
  'file_absent',
  'file_contains',
  'date_passed',
])

/** Claves permitidas dentro de file_contains. */
const CLAVES_FILE_CONTAINS = ['path', 'text']

/** True si todos los caracteres son digitos ASCII. */
function esDigitos(s) {
  for (const c of s) {
    if (c < '0' || c > '9') return false
  }
  return s.length > 0
}

/** True solo para un AAAA-MM-DD que ademas sea una fecha real del calendario. */
function esFechaISO(valor) {
  if (typeof valor !== 'string' || valor.length !== 10) return false
  if (valor[4] !== '-' || valor[7] !== '-') return false
  if (!esDigitos(valor.slice(0, 4))) return false
  if (!esDigitos(valor.slice(5, 7))) return false
  if (!esDigitos(valor.slice(8, 10))) return false
  const d = new Date(`${valor}T00:00:00Z`)
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === valor
}

/** Parte una ruta por "/" o "\" sin usar RegExp. */
function segmentos(p) {
  const out = []
  let actual = ''
  for (const c of p) {
    if (c === '/' || c === '\\') {
      out.push(actual)
      actual = ''
    } else {
      actual += c
    }
  }
  out.push(actual)
  return out
}

/** True si `p` es la propia raiz `r` o cuelga de ella. Comparacion de rutas ya reales. */
function contenida(p, r) {
  return p === r || p.startsWith(r + sep)
}

/**
 * Ruta real de `target`. Si `target` todavia no existe, resuelve el ancestro
 * existente mas cercano y le vuelve a colgar los segmentos que faltaban.
 * `target` ya viene resuelto, asi que esos segmentos nunca son ".." ni ".".
 *
 * Subir al padre SOLO esta justificado cuando el motivo del fallo es que la
 * ruta no existe (ENOENT, o ENOTDIR porque un ancestro es un fichero): en ese
 * caso el padre si resuelve y la contencion se sigue comprobando de verdad.
 * Ante cualquier otro codigo (ELOOP, EACCES, ENAMETOOLONG...) no sabemos
 * adonde apunta la ruta, y recolgar los segmentos se saltaria la comprobacion
 * de contencion entera. No saber es estado "error": se lanza.
 */
function rutaReal(target) {
  let actual = target
  const pendientes = []
  for (;;) {
    try {
      const real = realpathSync(actual)
      return pendientes.length === 0 ? real : join(real, ...pendientes)
    } catch (err) {
      const codigo = err && err.code
      if (codigo !== 'ENOENT' && codigo !== 'ENOTDIR') {
        throw new Error(
          `no se puede resolver la ruta real de ${target}: ${codigo || (err && err.message)}`,
        )
      }
      const padre = dirname(actual)
      if (padre === actual) return join(actual, ...pendientes)
      pendientes.unshift(basename(actual))
      actual = padre
    }
  }
}

/**
 * Resuelve una ruta relativa contra la raiz del repo y prohibe salir de ella.
 *
 * La contencion se comprueba sobre la ruta REAL: existsSync, readFileSync y
 * readdirSync siguen los enlaces simbolicos, asi que comparar solo prefijos de
 * cadena dejaria que un enlace dentro del repo convirtiese file_contains en un
 * oraculo de contenido sobre ficheros de fuera.
 *
 * Devuelve esa misma ruta REAL, no la logica. Devolver la logica dejaba la
 * decision y la operacion sobre resoluciones distintas: se comprobaba
 * rutaReal(target) y despues existsSync/readFileSync/readdirSync volvian a
 * seguir los enlaces por su cuenta sobre target. El informe cita la ruta que
 * escribio el autor (check.file_exists y compania), no esta, asi que no pierde
 * legibilidad por resolverla.
 */
export function resolveInRepo(repoRoot, relPath) {
  if (typeof relPath !== 'string') {
    throw new Error(`ruta invalida: se esperaba un string y llego ${typeof relPath}`)
  }
  const root = resolve(repoRoot)
  const target = resolve(root, relPath)
  if (!contenida(target, root)) {
    throw new Error(`ruta fuera del repositorio: ${relPath}`)
  }
  const real = rutaReal(target)
  if (!contenida(real, rutaReal(root))) {
    throw new Error(`ruta fuera del repositorio (enlace simbolico): ${relPath}`)
  }
  return real
}

/**
 * True si la ruta REAL `abs` esta escrita con la MISMA caja con la que cada
 * uno de sus segmentos aparece en el listado de su directorio.
 *
 * Es la pieza que hace que file_exists y file_contains distingan mayusculas
 * igual que matchGlob: existsSync y readFileSync delegan en el sistema de
 * ficheros, que en APFS no las distingue, y realpath en macOS devuelve la caja
 * que se le pidio, no la del disco. Preguntarle al listado del directorio es
 * la unica forma de que el veredicto no dependa del sistema de ficheros.
 *
 * `abs` viene siempre de resolveInRepo, asi que ya esta contenida en la raiz y
 * sus enlaces simbolicos intermedios ya estan resueltos.
 *
 * Si un ancestro no existe o no es un directorio, la ruta no existe: eso es un
 * "no" legitimo. Cualquier otro fallo al listar (permisos, por ejemplo) es no
 * saber, y no saber se lanza para que la memoria acabe en estado "error".
 */
function cajaExacta(repoRoot, abs) {
  const rootReal = rutaReal(resolve(repoRoot))
  const rel = relative(rootReal, abs)
  if (rel === '') return true
  if (rel === '..' || rel.startsWith(`..${sep}`)) {
    throw new Error(`ruta fuera del repositorio al comprobar la caja: ${abs}`)
  }
  let padre = rootReal
  for (const parte of segmentos(rel)) {
    if (parte === '' || parte === '.') continue
    let entradas
    try {
      entradas = readdirSync(padre)
    } catch (err) {
      const codigo = err && err.code
      if (codigo === 'ENOENT' || codigo === 'ENOTDIR') return false
      throw new Error(
        `no se puede listar ${padre} para comprobar la caja de ${abs}: ${codigo || (err && err.message)}`,
      )
    }
    if (!entradas.includes(parte)) return false
    padre = join(padre, parte)
  }
  return true
}

/**
 * Glob minimo: solo "*", dentro de un unico segmento.
 *
 * Matcher iterativo de dos punteros con retroceso sobre el ultimo "*". No se
 * construye ningun RegExp a partir de la entrada: el patron lo escribe un
 * agente y un RegExp con N asteriscos concatenados daba backtracking
 * combinatorio (un cuelgue, que el try/catch de classify no intercepta).
 * Coste O(len(pattern) * len(name)) en el peor caso.
 *
 * Todo caracter que no sea "*" es literal, la interrogacion incluida.
 */
export function matchGlob(pattern, name) {
  if (typeof pattern !== 'string' || typeof name !== 'string') {
    throw new Error('matchGlob espera dos strings')
  }
  let p = 0
  let n = 0
  let ultimoStar = -1 // posicion del ultimo "*" visto en el patron
  let reanudar = -1 // posicion en name desde la que reanudar tras ese "*"

  while (n < name.length) {
    if (p < pattern.length && pattern[p] === '*') {
      ultimoStar = p
      reanudar = n
      p += 1
    } else if (p < pattern.length && pattern[p] === name[n]) {
      p += 1
      n += 1
    } else if (ultimoStar !== -1) {
      // El comodin se come un caracter mas, pero nunca cruza de segmento.
      if (name[reanudar] === '/') return false
      reanudar += 1
      n = reanudar
      p = ultimoStar + 1
    } else {
      return false
    }
  }
  while (p < pattern.length && pattern[p] === '*') p += 1
  return p === pattern.length
}

/**
 * Motivo si la ruta esta mal formada, o null si pasa.
 *
 * `comodin` dice que hace el verbo con "*": "ultimo" lo acepta solo en el
 * ultimo segmento (file_matches, file_absent), "no" lo rechaza siempre
 * (file_exists, file_contains.path), porque esos dos abren una ruta EXACTA y
 * un "*" se comparara literalmente: nunca casa, y la comprobacion sale roja
 * para siempre sin que nadie se entere.
 */
function motivoRutaInvalida(clave, valor, comodin) {
  if (typeof valor !== 'string') {
    return `${clave} invalido: se esperaba un string y llego ${typeof valor}`
  }
  if (valor === '') {
    return `${clave} invalido: cadena vacia`
  }
  // Espacios al principio o al final son casi siempre una errata, y ademas
  // esquivan la deteccion de tautologia de mas abajo: "* " no es "solo
  // comodines" caracter a caracter, pero como patron no puede fallar nunca
  // (ningun nombre de fichero acaba en espacio), asi que file_absent con ese
  // valor sale verde para siempre. Se rechaza antes de llegar ahi.
  if (valor !== valor.trim()) {
    return `${clave} invalido: el patron ${JSON.stringify(valor)} lleva espacios al principio o al final`
  }
  if (comodin === 'no' && valor.includes('*')) {
    return `${clave} no admite comodines: use file_matches (o file_absent) para el patron ${valor}`
  }
  // Un "*" fuera del ultimo segmento no esta soportado. Tratarlo como literal
  // daria un veredicto inventado sobre un directorio que no es el que se
  // pretendia mirar, asi que es error y no verde.
  const partes = segmentos(valor)
  for (let i = 0; i < partes.length - 1; i += 1) {
    if (partes[i].includes('*')) {
      return `glob no soportado: "*" fuera del ultimo segmento en ${valor}`
    }
  }
  // Un ultimo segmento que es solo comodines casa con CUALQUIER entrada, asi
  // que file_matches sale verde en cuanto el directorio tenga algo dentro (y
  // con dirname "." ese directorio es la raiz del repo, que nunca esta vacia)
  // y file_absent sale verde solo si el directorio esta vacio o no existe. En
  // los dos casos la comprobacion no dice nada de lo que la memoria afirma:
  // es la comprobacion tautologica que el _readme de checks.json llama peor
  // que no tener comprobacion, porque da confianza falsa. Sin entrada la
  // memoria sale gris, que es un resultado honesto.
  if (comodin === 'ultimo') {
    const ultimo = partes[partes.length - 1]
    if (ultimo.length > 0 && !ultimo.split('').some((c) => c !== '*')) {
      return (
        `${clave} tautologico: el patron ${valor} casa con cualquier entrada, asi que nunca ` +
        'puede fallar; escriba la parte literal que la memoria afirma'
      )
    }
  }
  return null
}

/**
 * Dice si `check` es una comprobacion bien formada del vocabulario.
 * Devuelve {valido, motivo} y NO toca el disco: solo mira la forma.
 *
 * Vive aqui y no en load-checks.mjs para que la validacion de forma este en un
 * unico sitio: lo que rechaza el cargador de checks.json es exactamente lo que
 * rechaza el ejecutor.
 */
export function validateCheck(check) {
  const no = (motivo) => ({ valido: false, motivo })
  if (typeof check !== 'object' || check === null || Array.isArray(check)) {
    return no(`comprobacion invalida: se esperaba un objeto con una unica clave del vocabulario`)
  }
  const claves = Object.keys(check)
  if (claves.length === 0) {
    return no('comprobacion invalida: objeto sin ninguna clave')
  }
  if (claves.length > 1) {
    return no(`comprobacion invalida: mas de una clave (${claves.join(', ')})`)
  }
  const clave = claves[0]
  if (!VOCABULARIO.includes(clave)) {
    return no(`comprobacion desconocida: ${clave}`)
  }
  const valor = check[clave]

  if (clave === 'file_exists') {
    const motivo = motivoRutaInvalida(clave, valor, 'no')
    return motivo ? no(motivo) : { valido: true, motivo: null }
  }

  if (clave === 'file_matches' || clave === 'file_absent') {
    const motivo = motivoRutaInvalida(clave, valor, 'ultimo')
    return motivo ? no(motivo) : { valido: true, motivo: null }
  }

  if (clave === 'file_contains') {
    if (typeof valor !== 'object' || valor === null || Array.isArray(valor)) {
      return no('file_contains invalido: se esperaba un objeto {path, text}')
    }
    const extra = Object.keys(valor).filter((k) => !CLAVES_FILE_CONTAINS.includes(k))
    if (extra.length > 0) {
      return no(`file_contains invalido: claves desconocidas (${extra.join(', ')})`)
    }
    const motivoPath = motivoRutaInvalida('file_contains.path', valor.path, 'no')
    if (motivoPath) return no(motivoPath)
    if (typeof valor.text !== 'string') {
      return no(
        `file_contains.text invalido: se esperaba un string y llego ${typeof valor.text}`,
      )
    }
    // includes("") es siempre true: una comprobacion con texto vacio se
    // declararia verde para siempre. Mismo razonamiento que con text ausente.
    if (valor.text === '') {
      return no('file_contains.text invalido: cadena vacia')
    }
    return { valido: true, motivo: null }
  }

  // date_passed: sin formato estricto la comparacion es lexicografica y
  // silenciosa: "manana" o "2026-9-1" saldrian rojos sin que nadie lo note.
  if (!esFechaISO(valor)) {
    return no(`date_passed invalido: se esperaba una fecha AAAA-MM-DD y llego ${JSON.stringify(valor)}`)
  }
  return { valido: true, motivo: null }
}

/**
 * Estado de una ruta YA REAL, sin seguir un ultimo enlace.
 *
 * lstat y no stat a proposito: `abs` viene de resolveInRepo, que ya resolvio
 * los enlaces, asi que un enlace aqui solo puede ser uno roto (realpath fallo
 * con ENOENT) o uno creado despues de decidir la contencion. En los dos casos
 * seguirlo seria operar sobre algo distinto de lo que se comprobo.
 * Devuelve undefined si no hay nada.
 */
function estado(abs) {
  return lstatSync(abs, { throwIfNoEntry: false })
}

/**
 * Busca ficheros que casen con el patron. Devuelve {found, dirExists, dir}.
 *
 * El glob solo se aplica al ultimo segmento; la forma del patron ya la valida
 * validateCheck. Que el directorio no exista si es un verde legitimo para
 * file_absent (nada puede casar), pero el motivo tiene que decirlo para
 * distinguir "no hay nada" de "no miro donde usted creia".
 *
 * Si lo que hay en esa ruta no es un directorio, no se lista: readdirSync
 * sobre un FIFO o un socket no da un error limpio en todos los sistemas, y un
 * bloqueo no lo atrapa ningun try/catch. No saber es estado "error".
 */
function anyFileMatches(repoRoot, pattern) {
  const dir = dirname(pattern)
  const base = basename(pattern)
  const abs = resolveInRepo(repoRoot, dir)
  // el directorio escrito con otra caja no es este directorio: se trata igual
  // que si no existiese, que es lo que dice el listado de su padre
  if (!cajaExacta(repoRoot, abs)) return { found: false, dirExists: false, dir, roto: false }
  const st = estado(abs)
  if (!st) return { found: false, dirExists: false, dir, roto: false }
  if (st.isSymbolicLink()) return { found: false, dirExists: false, dir, roto: true }
  if (!st.isDirectory()) {
    throw new Error(`${dir} no es un directorio: no se puede listar para resolver ${pattern}`)
  }
  return {
    found: readdirSync(abs).some((name) => matchGlob(base, name)),
    dirExists: true,
    dir,
    roto: false,
  }
}

/** Motivo de "no casa nada", diciendo si el directorio ni siquiera esta. */
function motivoSinCoincidencias(pattern, dirExists, dir, roto) {
  if (dirExists) return `no hay nada que case con ${pattern}`
  const detalle = roto ? ' (enlace roto)' : ''
  return `no hay nada que case con ${pattern}: el directorio ${dir} no existe${detalle}`
}

/**
 * Evalua una comprobacion. Devuelve {ok, reason}; lanza si esta mal formada o
 * si no se puede saber la respuesta (el auditor lo traduce a estado "error").
 */
export function runCheck(check, { repoRoot, today }) {
  const forma = validateCheck(check)
  if (!forma.valido) throw new Error(forma.motivo)

  if ('file_exists' in check) {
    // existsSync decide la existencia (un enlace roto no existe); cajaExacta
    // decide que sea ESTA entrada y no una que solo difiere en mayusculas
    const abs = resolveInRepo(repoRoot, check.file_exists)
    const ok = existsSync(abs) && cajaExacta(repoRoot, abs)
    return { ok, reason: ok ? `existe ${check.file_exists}` : `no existe ${check.file_exists}` }
  }
  if ('file_matches' in check) {
    const { found, dirExists, dir, roto } = anyFileMatches(repoRoot, check.file_matches)
    if (found) return { ok: true, reason: `existe algo que casa con ${check.file_matches}` }
    return { ok: false, reason: motivoSinCoincidencias(check.file_matches, dirExists, dir, roto) }
  }
  if ('file_absent' in check) {
    const { found, dirExists, dir, roto } = anyFileMatches(repoRoot, check.file_absent)
    if (found) {
      return { ok: false, reason: `todavia existe algo que casa con ${check.file_absent}` }
    }
    return { ok: true, reason: motivoSinCoincidencias(check.file_absent, dirExists, dir, roto) }
  }
  if ('file_contains' in check) {
    const { path, text } = check.file_contains
    const abs = resolveInRepo(repoRoot, path)
    const st = estado(abs)
    // Un enlace roto no existe tampoco para existsSync: mismo veredicto que
    // file_exists sobre esa ruta, y sin abrir nada.
    // la caja se comprueba ANTES de abrir nada: una ruta escrita con otra caja
    // no es este fichero, y leerlo seria responder por un fichero distinto
    if (!st || st.isSymbolicLink() || !cajaExacta(repoRoot, abs)) {
      return { ok: false, reason: `no existe ${path}` }
    }
    if (!st.isFile()) {
      // Abrir un FIFO sin escritor bloquea el proceso para siempre, y un
      // cuelgue no lo atrapa ningun try/catch: se mira el tipo ANTES de leer.
      throw new Error(`${path} no es un fichero regular: no se puede leer su contenido`)
    }
    const ok = readFileSync(abs, 'utf8').includes(text)
    return { ok, reason: ok ? `${path} contiene "${text}"` : `${path} ya no contiene "${text}"` }
  }

  const fecha = check.date_passed
  if (!esFechaISO(today)) {
    throw new Error(`fecha de hoy invalida: se esperaba AAAA-MM-DD y llego ${JSON.stringify(today)}`)
  }
  const ok = fecha <= today
  // Si la fecha no ha llegado la afirmacion "ya paso" todavia no es cierta: no
  // ha caducado nada. El motivo lo dice asi para que el informe no acuse de
  // obsolescencia a algo que aun no ha ocurrido.
  return {
    ok,
    reason: ok ? `${fecha} ya paso` : `${fecha} todavia no ha llegado: la fecha aun esta por venir`,
  }
}
