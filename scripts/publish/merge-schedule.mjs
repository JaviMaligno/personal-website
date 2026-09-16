#!/usr/bin/env node
import { readFileSync, writeFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { mergeSchedules } from './schedule.mjs'

// Git driver: %O (ancestor), %A (ours/output), %B (theirs).
// Do not overwrite %A until reconciliation and validation both succeed.
try {
  const [basePath, oursPath, theirsPath] = process.argv.slice(2)
  if (!basePath || !oursPath || !theirsPath) throw new Error('Expected %O %A %B')
  const read = path => {
    const text = readFileSync(path, 'utf8')
    return text.trim() ? JSON.parse(text) : { articles: [] }
  }
  const published = new Set(execFileSync('git', ['ls-tree', '-r', '--name-only', 'HEAD'], { encoding: 'utf8' }).trim().split('\n'))
  const merged = mergeSchedules(read(basePath), read(oursPath), read(theirsPath), {
    isPublished: entry => published.has(entry.article),
  })
  writeFileSync(oursPath, JSON.stringify(merged, null, 2) + '\n')
} catch (error) {
  console.error(`::error::${error.message}`)
  process.exitCode = 1
}
