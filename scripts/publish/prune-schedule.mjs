#!/usr/bin/env node
import { readFileSync, writeFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { pruneSchedule } from './schedule.mjs'

try {
  const path = '.github/publish-schedule.json'
  const manifest = JSON.parse(readFileSync(path, 'utf8'))
  // The merged index includes the article being published; untracked drafts
  // must never make pending entries disappear.
  const tracked = new Set(execFileSync('git', ['ls-files', '--cached'], { encoding: 'utf8' }).trim().split('\n'))
  const linkedin = JSON.parse(readFileSync('scripts/linkedin/posts/schedule.json', 'utf8'))
  const published = new Set(execFileSync('git', ['ls-tree', '-r', '--name-only', 'HEAD'], { encoding: 'utf8' }).trim().split('\n'))
  // Check dates while the new article is still pending. Otherwise pruning it
  // could hide a collision from a textual merge that never invoked the driver.
  pruneSchedule(manifest, entry => published.has(entry.article), linkedin)
  const pending = pruneSchedule(manifest, entry => tracked.has(entry.article), linkedin)
  writeFileSync(path, JSON.stringify(pending, null, 2) + '\n')
  console.log(`Schedule: ${manifest.articles.length - pending.articles.length} published entries removed; ${pending.articles.length} pending.`)
} catch (error) {
  console.error(`::error::${error.message}`)
  process.exitCode = 1
}
