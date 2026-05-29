// i18n consistency checker
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, '..')
const localesDir = path.join(root, 'src', 'i18n', 'locales')

const zh = JSON.parse(fs.readFileSync(path.join(localesDir, 'zh-CN.json'), 'utf8'))
const en = JSON.parse(fs.readFileSync(path.join(localesDir, 'en.json'), 'utf8'))

// Flatten nested object into dotted keys
function flatten(obj, prefix = '', out = {}) {
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      flatten(v, key, out)
    } else {
      out[key] = v
    }
  }
  return out
}

const zhFlat = flatten(zh)
const enFlat = flatten(en)
const zhKeys = new Set(Object.keys(zhFlat))
const enKeys = new Set(Object.keys(enFlat))

const inZhNotEn = [...zhKeys].filter((k) => !enKeys.has(k)).sort()
const inEnNotZh = [...enKeys].filter((k) => !zhKeys.has(k)).sort()

console.log('=== Keys in zh-CN but MISSING in en (' + inZhNotEn.length + ') ===')
inZhNotEn.forEach((k) => console.log('  ' + k))
console.log('\n=== Keys in en but MISSING in zh-CN (' + inEnNotZh.length + ') ===')
inEnNotZh.forEach((k) => console.log('  ' + k))

// Keys whose value is identical to the key path (untranslated placeholder)
const zhSameAsKey = Object.entries(zhFlat).filter(([k, v]) => v === k).map(([k]) => k)
if (zhSameAsKey.length) {
  console.log('\n=== zh-CN values equal to key path (suspicious) (' + zhSameAsKey.length + ') ===')
  zhSameAsKey.forEach((k) => console.log('  ' + k))
}

console.log('\nzh total:', zhKeys.size, ' en total:', enKeys.size)
