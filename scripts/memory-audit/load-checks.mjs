// scripts/memory-audit/load-checks.mjs
// Carga y valida checks.json: las comprobaciones de vigencia, indexadas por
// nombre de memoria.
//
// Las comprobaciones viven en el repositorio, no en el frontmatter de cada
// memoria. Dos motivos:
//   1. privacidad: las memorias son privadas y este repositorio es publico,
//      asi que el auditor solo puede conocer NOMBRES de memoria, nunca cuerpos;
//   2. fiabilidad: parsear a mano el YAML de un fichero que escribe un agente
//      resulto ser la causa comun de casi todos los falsos verdes y grises.
//
// Regla de oro: cuando no se puede saber si una entrada dice lo que parece
// decir, va a `errors` y su memoria acaba en estado "error". Nunca en verde
// (dejaria pasar una memoria caducada) ni en gris (la escondaria del informe).

import { VOCABULARIO, validateCheck } from './checks.mjs'

// El vocabulario y la validacion de forma son los de checks.mjs, no una copia.
// Este modulo tenia los suyos, y el suyo solo miraba que la clave existiese: una
// comprobacion con valor invalido (una fecha "manana", un file_contains sin
// text) pasaba la carga y solo reventaba al ejecutarse, ya dentro de la
// auditoria. Con dos validadores tambien bastaba con anadir un verbo en
// checks.mjs para que aqui saliese "desconocido" y la memoria dejase de
// vigilarse. Se reexporta para que quien use el cargador no tenga que ir a
// buscarlo al ejecutor.
export { VOCABULARIO }

// Un nombre de fichero de memoria: letra o digito y despues los caracteres que
// usan estos ficheros. Deja fuera rutas, saltos de linea, nombres ocultos y
// claves internas del JSON como "__proto__".
const NOMBRE_MEMORIA = /^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$/

const MAX_TEXTO = 120

function esObjeto(v) {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

/** Nombre del tipo para los mensajes, distinguiendo null y array de "object". */
function tipo(v) {
  if (v === null) return 'null'
  if (Array.isArray(v)) return 'array'
  return typeof v
}

/** Recorta lo que venga del fichero antes de meterlo en un mensaje de error. */
function recorta(v) {
  const texto = typeof v === 'string' ? v : String(v)
  return texto.length > MAX_TEXTO ? `${texto.slice(0, MAX_TEXTO)}...` : texto
}

/** True si la clave puede ser el nombre de un fichero de memoria. */
export function esNombreMemoriaPlausible(clave) {
  return typeof clave === 'string' && !clave.includes('..') && NOMBRE_MEMORIA.test(clave)
}

/**
 * Valida una entrada de "memories".
 * Devuelve {checks, revalidate, errors}: `checks` solo trae las comprobaciones
 * bien formadas, pero si `errors` no esta vacio la memoria sale "error" y esas
 * comprobaciones no llegan a ejecutarse. Nunca se ejecuta media entrada.
 */
function validarEntrada(valor) {
  if (!esObjeto(valor)) {
    return { checks: [], revalidate: null, errors: [`se esperaba un objeto y llego ${tipo(valor)}`] }
  }
  const errors = []

  for (const clave of Object.keys(valor)) {
    // una errata como "chekcs" dejaria la memoria en gris sin que nadie lo note
    if (clave !== 'checks' && clave !== 'revalidate') {
      errors.push(`clave desconocida en la entrada: ${recorta(clave)}`)
    }
  }

  let revalidate = null
  if ('revalidate' in valor) {
    if (typeof valor.revalidate !== 'string' || valor.revalidate.trim() === '') {
      errors.push(`revalidate invalido: se esperaba un string no vacio y llego ${tipo(valor.revalidate)}`)
    } else {
      revalidate = valor.revalidate
    }
  }

  const checks = []
  if ('checks' in valor) {
    if (!Array.isArray(valor.checks)) {
      errors.push(`checks invalido: se esperaba un array y llego ${tipo(valor.checks)}`)
    } else if (valor.checks.length === 0) {
      // un array vacio suele ser una entrada a medio escribir, no una memoria
      // sin comprobacion: para eso se borra la entrada o se deja solo revalidate
      errors.push('checks vacio: borre la entrada o dejela solo con revalidate')
    } else {
      valor.checks.forEach((check, i) => {
        // misma validacion que usa runCheck: lo que rechaza el ejecutor se
        // rechaza aqui, y no al vuelo en mitad de la auditoria
        const { valido, motivo } = validateCheck(check)
        if (!valido) errors.push(`comprobacion ${i + 1}: ${recorta(motivo)}`)
        else checks.push(check)
      })
    }
  }

  return { checks, revalidate, errors }
}

// Tope de anidamiento del recorrido de claves duplicadas. checks.json tiene
// cuatro niveles; con mas que esto no es un fichero de comprobaciones escrito a
// mano, y recorrerlo recursivamente sin tope tumbaria el proceso.
const MAX_PROFUNDIDAD = 64

const BLANCOS_JSON = [' ', '\t', '\n', '\r']

/**
 * Claves duplicadas en el TEXTO de un JSON, que JSON.parse pierde en silencio.
 *
 * JSON.parse aplica last-wins: si una memoria aparece dos veces, la PRIMERA
 * entrada desaparece sin rastro y la comprobacion que su autor cree activa no
 * se ejecuta jamas. Sobre el objeto parseado eso ya no se puede ver, asi que
 * hace falta recorrer el texto.
 *
 * Solo mira la forma: no interpreta numeros ni literales, solo necesita saber
 * donde empieza y acaba cada string para no confundir una llave dentro de un
 * valor con el principio de un objeto. Las claves se comparan ya decodificadas,
 * como las compara JSON.parse, para que "m" y "m" cuenten como la misma.
 *
 * Devuelve una lista de {ruta, clave, veces}. Lanza si el texto no se puede
 * recorrer: no saber si hay duplicados es "error", nunca un silencio.
 */
export function findDuplicateKeys(texto) {
  let i = 0
  const duplicadas = []

  const fallo = (msg) => {
    throw new Error(`${msg} (posicion ${i})`)
  }

  function saltarBlancos() {
    while (i < texto.length && BLANCOS_JSON.includes(texto[i])) i += 1
  }

  /** Lee el string que empieza en `i` y devuelve su valor ya decodificado. */
  function leerString() {
    i += 1
    let out = ''
    while (i < texto.length) {
      const c = texto[i]
      if (c === '"') {
        i += 1
        return out
      }
      if (c !== '\\') {
        out += c
        i += 1
        continue
      }
      const escapado = texto[i + 1]
      i += 2
      if (escapado === 'u') {
        const hex = texto.slice(i, i + 4)
        if (hex.length < 4) fallo('escape unicode incompleto')
        const codigo = Number.parseInt(hex, 16)
        if (Number.isNaN(codigo)) fallo('escape unicode invalido')
        out += String.fromCharCode(codigo)
        i += 4
        continue
      }
      const simples = { '"': '"', '\\': '\\', '/': '/', b: '\b', f: '\f', n: '\n', r: '\r', t: '\t' }
      if (!(escapado in simples)) fallo('escape desconocido en un string')
      out += simples[escapado]
    }
    return fallo('string sin cerrar')
  }

  function objeto(ruta, profundidad) {
    i += 1 // la '{'
    const vistas = new Map()
    saltarBlancos()
    if (texto[i] === '}') {
      i += 1
      return
    }
    for (;;) {
      saltarBlancos()
      if (texto[i] !== '"') fallo('se esperaba una clave entre comillas')
      const clave = leerString()
      vistas.set(clave, (vistas.get(clave) ?? 0) + 1)
      saltarBlancos()
      if (texto[i] !== ':') fallo('se esperaba ":" despues de una clave')
      i += 1
      valor([...ruta, clave], profundidad + 1)
      saltarBlancos()
      if (texto[i] === ',') {
        i += 1
        continue
      }
      if (texto[i] === '}') {
        i += 1
        break
      }
      fallo('se esperaba "," o "}"')
    }
    for (const [clave, veces] of vistas) {
      if (veces > 1) duplicadas.push({ ruta, clave, veces })
    }
  }

  function lista(ruta, profundidad) {
    i += 1 // la '['
    saltarBlancos()
    if (texto[i] === ']') {
      i += 1
      return
    }
    let indice = 0
    for (;;) {
      valor([...ruta, String(indice)], profundidad + 1)
      indice += 1
      saltarBlancos()
      if (texto[i] === ',') {
        i += 1
        continue
      }
      if (texto[i] === ']') {
        i += 1
        break
      }
      fallo('se esperaba "," o "]"')
    }
  }

  function valor(ruta, profundidad) {
    if (profundidad > MAX_PROFUNDIDAD) {
      fallo(`JSON con mas de ${MAX_PROFUNDIDAD} niveles de anidamiento`)
    }
    saltarBlancos()
    const c = texto[i]
    if (c === undefined) fallo('se esperaba un valor y se acabo el texto')
    if (c === '{') return objeto(ruta, profundidad)
    if (c === '[') return lista(ruta, profundidad)
    if (c === '"') {
      leerString()
      return
    }
    // numero, true, false o null: se consumen sin interpretarlos, porque para
    // buscar claves duplicadas da igual lo que valgan
    const inicio = i
    while (i < texto.length && !BLANCOS_JSON.includes(texto[i]) && !',}]'.includes(texto[i])) i += 1
    if (i === inicio) fallo('valor inesperado')
    return undefined
  }

  valor([], 0)
  saltarBlancos()
  if (i < texto.length) fallo('texto sobrante despues del valor de primer nivel')
  return duplicadas
}

/** Nombre legible de la ruta de un objeto dentro de checks.json. */
function rutaLegible(ruta) {
  return ruta.length === 0 ? 'la raiz' : ruta.map((p) => recorta(p)).join(' > ')
}

/**
 * La memoria a la que hay que imputar una clave duplicada, o null si la
 * duplicidad no cae dentro de ninguna entrada de "memories".
 */
function memoriaAfectada({ ruta, clave }) {
  if (ruta.length === 1 && ruta[0] === 'memories') return clave
  if (ruta.length >= 2 && ruta[0] === 'memories') return ruta[1]
  return null
}

/**
 * Carga el texto de checks.json.
 *
 * Devuelve {entries, errors, fatal}:
 *   entries  Map de nombre de memoria -> {name, checks, revalidate, errors}.
 *            Una entrada con `errors` sigue en el mapa a proposito: asi su
 *            memoria sale "error" y no gris.
 *   errors   lista plana de problemas, para el informe.
 *   fatal    true si el fichero entero es inservible (JSON invalido, raiz que
 *            no es objeto, sin "memories", "memories" repetida, o claves
 *            duplicadas que no se pueden comprobar). Con fatal no se puede
 *            auditar nada: sin entradas, TODAS las memorias saldrian grises,
 *            que es justo el falso gris que esta herramienta existe para
 *            evitar.
 *
 * Las claves duplicadas se buscan sobre el TEXTO, no sobre el objeto parseado:
 * ahi last-wins ya se aplico y la duplicidad se perdio. Una memoria repetida
 * queda con error (no se sabe cual de las dos versiones vale), nunca con el
 * veredicto de la unica que sobrevivio al parseo.
 */
export function loadChecks(rawJson) {
  const entries = new Map()

  if (typeof rawJson !== 'string') {
    return { entries, errors: [`checks.json: se esperaba texto y llego ${tipo(rawJson)}`], fatal: true }
  }

  let raiz
  try {
    raiz = JSON.parse(rawJson)
  } catch (err) {
    // un JSON roto es un error limpio, no una excepcion que tumbe la auditoria
    return { entries, errors: [`checks.json: JSON invalido: ${err.message}`], fatal: true }
  }

  if (!esObjeto(raiz)) {
    return { entries, errors: [`checks.json: la raiz tiene que ser un objeto y es ${tipo(raiz)}`], fatal: true }
  }
  if (!('memories' in raiz)) {
    return { entries, errors: ['checks.json: falta la clave "memories"'], fatal: true }
  }
  if (!esObjeto(raiz.memories)) {
    return {
      entries,
      errors: [`checks.json: "memories" tiene que ser un objeto y es ${tipo(raiz.memories)}`],
      fatal: true,
    }
  }

  // El objeto parseado ya no sabe si alguna clave venia repetida: last-wins se
  // aplico en silencio. Hay que preguntarselo al texto.
  let duplicadas
  try {
    duplicadas = findDuplicateKeys(rawJson)
  } catch (err) {
    // no se puede saber cuantas entradas se perdieron por el camino, y auditar
    // con entradas perdidas convierte esas memorias en grises falsas
    return {
      entries,
      errors: [`checks.json: no se pueden comprobar las claves duplicadas: ${err.message}`],
      fatal: true,
    }
  }

  const errors = []
  // errores de duplicidad imputados a cada memoria, para que salga "error" y no
  // el veredicto de la unica mitad que sobrevivio al parseo
  const duplicadasPorMemoria = new Map()

  for (const d of duplicadas) {
    const mensaje =
      `clave duplicada en ${rutaLegible(d.ruta)}: ${JSON.stringify(recorta(d.clave))} aparece ` +
      `${d.veces} veces y JSON.parse se queda solo con la ultima`
    errors.push(`checks.json: ${mensaje}`)

    if (d.ruta.length === 0 && d.clave === 'memories') {
      // se perdio un bloque entero de entradas: las memorias que estaban en el
      // saldrian grises, que es el informe tranquilizador y falso de siempre
      return { entries, errors, fatal: true }
    }
    const memoria = memoriaAfectada(d)
    if (memoria !== null) {
      const previos = duplicadasPorMemoria.get(memoria) ?? []
      previos.push(mensaje)
      duplicadasPorMemoria.set(memoria, previos)
    }
  }

  for (const clave of Object.keys(raiz)) {
    if (clave !== '_readme' && clave !== 'memories') {
      errors.push(`checks.json: clave de primer nivel desconocida: ${recorta(clave)}`)
    }
  }

  for (const [clave, valor] of Object.entries(raiz.memories)) {
    if (!esNombreMemoriaPlausible(clave)) {
      // no se indexa: una clave asi no puede casar con ningun nombre de
      // memoria, y tratarla como tal seria inventarse a que memoria apunta
      errors.push(`checks.json: nombre de memoria no plausible: ${JSON.stringify(recorta(clave))}`)
      continue
    }
    const entrada = validarEntrada(valor)
    for (const e of entrada.errors) errors.push(`checks.json: ${clave}: ${e}`)
    // la duplicidad invalida la entrada entera: no se sabe cual de las dos
    // versiones queria su autor, asi que no se ejecuta ninguna
    const suyos = duplicadasPorMemoria.get(clave) ?? []
    entries.set(clave, { name: clave, ...entrada, errors: [...entrada.errors, ...suyos] })
  }

  return { entries, errors, fatal: false }
}
