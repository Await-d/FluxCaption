// Find t('...') keys used in code and check they exist in locale files
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, '..')
const srcDir = path.join(root, 'src')
const localesDir = path.join(srcDir, 'i18n', 'locales')

const zh = JSON.parse(fs.readFileSync(path.join(localesDir, 'zh-CN.json'), 'utf8'))
const en = JSON.parse(fs.readFileSync(path.join(localesDir, 'en.json'), 'utf8'))

function flatten(obj, prefix = '', out = {}) {
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object' && !Array.isArray(v)) flatten(v, key, out)
    else out[key] = v
  }
  return out
}

const zhKeys = new Set(Object.keys(flatten(zh)))
const enKeys = new Set(Object.keys(flatten(en)))

// Walk source files
function walk(dir, files = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name === 'i18n') continue
      walk(p, files)
    } else if (/\.(tsx?|jsx?)$/.test(entry.name)) {
      files.push(p)
    }
  }
  return files
}

const files = walk(srcDir)

// Match t('key'), t("key"), t(`key`) — only static string keys (first arg)
const staticKeyRe = /\bt\(\s*(['"`])([A-Za-z0-9_.-]+)\1/g
// Dynamic template usage like t(`languages.${x}`) — flag separately
const dynamicRe = /\bt\(\s*`[^`]*\$\{/g

const used = new Map() // key -> [files]
const dynamicFiles = new Set()

for (const f of files) {
  const code = fs.readFileSync(f, 'utf8')
  let m
  while ((m = staticKeyRe.exec(code))) {
    const key = m[2]
    if (!key.includes('.')) continue // skip non-namespaced false positives
    if (!used.has(key)) used.set(key, new Set())
    used.get(key).add(path.relative(root, f))
  }
  if (dynamicRe.test(code)) dynamicFiles.add(path.relative(root, f))
}

const missingInBoth = []
const missingInZh = []
const missingInEn = []

for (const [key, fileSet] of used) {
  const inZh = zhKeys.has(key)
  const inEn = enKeys.has(key)
  if (!inZh && !inEn) missingInBoth.push([key, [...fileSet]])
  else if (!inZh) missingInZh.push([key, [...fileSet]])
  else if (!inEn) missingInEn.push([key, [...fileSet]])
}

const sortByKey = (a, b) => a[0].localeCompare(b[0])

console.log('=== Used keys MISSING in BOTH locales (' + missingInBoth.length + ') ===')
missingInBoth.sort(sortByKey).forEach(([k, fs]) => console.log(`  ${k}  <- ${fs.join(', ')}`))

console.log('\n=== Used keys MISSING in zh-CN only (' + missingInZh.length + ') ===')
missingInZh.sort(sortByKey).forEach(([k]) => console.log(`  ${k}`))

console.log('\n=== Used keys MISSING in en only (' + missingInEn.length + ') ===')
missingInEn.sort(sortByKey).forEach(([k]) => console.log(`  ${k}`))

console.log('\n=== Files with dynamic t(`...${}`) keys (review manually) (' + dynamicFiles.size + ') ===')
;[...dynamicFiles].sort().forEach((f) => console.log('  ' + f))
