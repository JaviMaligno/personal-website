import { isDeepStrictEqual } from 'node:util'
import { validateManifest } from './select-due-article.mjs'

function checkShape(manifest) {
  const errors = validateManifest(manifest)
  if (errors.length) throw new Error(errors.join('; '))
}

// A date passing does not mean publication succeeded. Only the article's
// presence in the relevant Git tree makes an entry eligible for removal.
export function pruneSchedule(manifest, isPublished, linkedin = []) {
  checkShape(manifest)
  const articles = manifest.articles.filter(e => !isPublished(e))
    .sort((a, b) => a.date.localeCompare(b.date) || a.slug.localeCompare(b.slug))
  const dates = new Map()
  for (const entry of articles) {
    if (dates.has(entry.date)) {
      throw new Error(`Schedule date conflict on ${entry.date}: ${dates.get(entry.date)} and ${entry.slug}`)
    }
    if (linkedin.some(post => post.date === entry.date)) {
      throw new Error(`Schedule date conflict with LinkedIn on ${entry.date}: ${entry.slug}`)
    }
    dates.set(entry.date, entry.slug)
  }
  return { ...manifest, articles }
}

function reconcile(base, ours, theirs, label) {
  if (isDeepStrictEqual(ours, theirs) || isDeepStrictEqual(theirs, base)) return ours
  if (isDeepStrictEqual(ours, base)) return theirs
  throw new Error(`Schedule conflict in ${label}: incompatible changes (including deletion versus edit)`)
}

export function mergeSchedules(base, ours, theirs, { isPublished = () => false } = {}) {
  for (const value of [base, ours, theirs]) checkShape(value)
  const maps = [base, ours, theirs].map(value => new Map(
    value.articles.filter(e => !isPublished(e)).map(e => [e.slug, e]),
  ))
  const slugs = new Set(maps.flatMap(map => [...map.keys()]))
  const articles = [...slugs].flatMap(slug => {
    const value = reconcile(...maps.map(map => map.get(slug)), `article ${slug}`)
    return value === undefined ? [] : [value]
  })
  const metadata = {}
  for (const key of new Set([base, ours, theirs].flatMap(Object.keys))) {
    if (key === 'articles') continue
    const value = reconcile(base[key], ours[key], theirs[key], key)
    if (value !== undefined) Object.defineProperty(metadata, key, { value, enumerable: true })
  }
  return pruneSchedule({ ...metadata, articles }, () => false)
}
