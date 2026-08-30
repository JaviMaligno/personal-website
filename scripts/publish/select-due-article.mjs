#!/usr/bin/env node
// Elige que articulo del manifiesto toca publicar, si es que toca alguno.
//
// La logica de seleccion es una funcion pura (selectDueArticle) para poder
// probarla sin git ni red; el CLI de abajo es el unico que toca el disco.
// Ver scripts/publish/select-due-article.test.mjs.

import { appendFileSync, existsSync, readFileSync } from 'node:fs'

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/

/**
 * Valida una entrada del manifiesto. Devuelve un array de errores (vacio = ok).
 * Se valida en cada ejecucion, no solo al escribirla: una entrada mal formada
 * tiene que fallar en voz alta el dia que se anade, no callarse hasta su fecha.
 */
export function validateEntry(entry, index) {
  const where = `articles[${index}]${entry?.slug ? ` (${entry.slug})` : ''}`
  const errors = []
  for (const field of ['slug', 'branch', 'article', 'date']) {
    if (typeof entry?.[field] !== 'string' || entry[field].trim() === '') {
      errors.push(`${where}: falta el campo obligatorio "${field}"`)
    }
  }
  if (typeof entry?.date === 'string' && !ISO_DATE.test(entry.date)) {
    errors.push(`${where}: "date" debe ser YYYY-MM-DD, no "${entry.date}"`)
  }
  if (entry?.blockIfMatches !== undefined) {
    try {
      new RegExp(entry.blockIfMatches)
    } catch (e) {
      errors.push(`${where}: "blockIfMatches" no es una regexp valida: ${e.message}`)
    }
  }
  return errors
}

export function validateManifest(manifest) {
  if (!Array.isArray(manifest?.articles)) {
    return ['el manifiesto no tiene un array "articles"']
  }
  const errors = manifest.articles.flatMap(validateEntry)
  const seen = new Map()
  for (const [i, entry] of manifest.articles.entries()) {
    if (typeof entry?.slug !== 'string') continue
    if (seen.has(entry.slug)) {
      errors.push(`articles[${i}] (${entry.slug}): slug duplicado, ya usado en articles[${seen.get(entry.slug)}]`)
    }
    seen.set(entry.slug, i)
  }
  return errors
}

/**
 * @param {object}   o
 * @param {object[]} o.entries    entradas del manifiesto, ya validadas.
 * @param {string}   o.today      fecha ISO de hoy en UTC.
 * @param {boolean}  o.alreadyPublishedToday  si main ya lleva una publicacion de hoy.
 * @param {(entry) => boolean} o.isPublished  si el articulo ya esta en main.
 * @returns {{action: 'publish'|'none', entry?: object, backlog?: number, reason?: string}}
 */
export function selectDueArticle({ entries, today, alreadyPublishedToday, isPublished }) {
  // Un articulo al dia. Si hay dos vencidos, el segundo espera a manana: publicar
  // los dos de golpe sacaria dos posts de LinkedIn el mismo dia, que es justo lo
  // que las fechas alternas existen para evitar.
  if (alreadyPublishedToday) {
    return { action: 'none', reason: 'main ya lleva una publicacion de hoy' }
  }

  const due = entries
    .filter((e) => e.date <= today)
    .filter((e) => !isPublished(e))
    .sort((a, b) => a.date.localeCompare(b.date) || a.slug.localeCompare(b.slug))

  if (due.length === 0) {
    return { action: 'none', reason: `nada vencido y sin publicar a fecha ${today}` }
  }
  // El mas antiguo primero: si se acumulo retraso, se drena en orden.
  return { action: 'publish', entry: due[0], backlog: due.length - 1 }
}

// ---------------------------------------------------------------- CLI

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`)
  return i === -1 ? fallback : process.argv[i + 1]
}

function main() {
  const manifestPath = arg('manifest', '.github/publish-schedule.json')
  const today = arg('today', new Date().toISOString().slice(0, 10))
  const forcedSlug = arg('slug', '')
  const alreadyPublishedToday = arg('published-today', 'false') === 'true'

  const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'))
  const errors = validateManifest(manifest)
  if (errors.length > 0) {
    for (const e of errors) console.error(`::error::${manifestPath}: ${e}`)
    process.exit(2)
  }

  const isPublished = (entry) => existsSync(entry.article)

  let result
  if (forcedSlug) {
    // workflow_dispatch con un slug: salta la fecha, pero NO el resto de guardas.
    // Sirve para recuperar un atraso a mano sin tocar el manifiesto.
    const entry = manifest.articles.find((e) => e.slug === forcedSlug)
    if (!entry) {
      console.error(`::error::slug "${forcedSlug}" no esta en ${manifestPath}`)
      process.exit(2)
    }
    result = isPublished(entry)
      ? { action: 'none', reason: `${entry.article} ya esta en main` }
      : { action: 'publish', entry, backlog: 0, forced: true }
  } else {
    result = selectDueArticle({
      entries: manifest.articles,
      today,
      alreadyPublishedToday,
      isPublished,
    })
  }

  if (result.action === 'none') {
    console.log(`Nada que publicar: ${result.reason}.`)
  } else {
    const extra = result.backlog > 0 ? ` (${result.backlog} mas en cola, para los dias siguientes)` : ''
    console.log(`A publicar: ${result.entry.slug} desde ${result.entry.branch}${extra}`)
  }

  if (process.env.GITHUB_OUTPUT) {
    const out = [`action=${result.action}`]
    if (result.entry) {
      out.push(
        `slug=${result.entry.slug}`,
        `branch=${result.entry.branch}`,
        `article=${result.entry.article}`,
        `date=${result.entry.date}`,
        `block_if_matches=${result.entry.blockIfMatches ?? ''}`,
        `block_reason=${(result.entry.blockReason ?? '').replace(/\n/g, ' ')}`,
      )
    }
    appendFileSync(process.env.GITHUB_OUTPUT, out.join('\n') + '\n')
  }
}

if (import.meta.url === `file://${process.argv[1]}`) main()
