import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { gzipSync } from 'node:zlib'

const INITIAL_BUNDLE_LIMIT_KIB = 200
const distDir = join(process.cwd(), 'dist')
const html = readFileSync(join(distDir, 'index.html'), 'utf8')
const assetNames = [...html.matchAll(/(?:src|href)="\/assets\/([^"]+\.(?:js|css))"/g)]
  .map((match) => match[1])

const gzipBytes = assetNames.reduce((total, assetName) => {
  const asset = readFileSync(join(distDir, 'assets', assetName))
  return total + gzipSync(asset).byteLength
}, 0)

const gzipKib = gzipBytes / 1024
if (gzipKib > INITIAL_BUNDLE_LIMIT_KIB) {
  throw new Error(
    `首屏资源 ${gzipKib.toFixed(2)} KiB gzip，超过 ${INITIAL_BUNDLE_LIMIT_KIB} KiB 限制`,
  )
}

console.log(
  `[bundle-size] 首屏资源 ${gzipKib.toFixed(2)} KiB gzip / ${INITIAL_BUNDLE_LIMIT_KIB} KiB`,
)
