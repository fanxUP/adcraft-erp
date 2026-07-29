import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import ts from 'typescript'
import { fileURLToPath } from 'node:url'

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = path.resolve(frontendRoot, '..')
const contractPath = path.join(
  repositoryRoot,
  'backend/app/ai_assistant/contracts/page_capabilities.json',
)
const routerPath = path.join(frontendRoot, 'src/router/index.ts')

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'))
}

function stringProperty(objectNode, propertyName) {
  for (const property of objectNode.properties) {
    if (!ts.isPropertyAssignment(property)) continue
    const name = property.name.getText().replace(/^['"]|['"]$/g, '')
    if (name !== propertyName || !ts.isStringLiteral(property.initializer)) continue
    return property.initializer.text
  }
  return null
}

function collectNamedRoutes(sourceText) {
  const sourceFile = ts.createSourceFile(
    routerPath,
    sourceText,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TS,
  )
  const routes = new Map()
  const visit = (node) => {
    if (ts.isObjectLiteralExpression(node)) {
      const name = stringProperty(node, 'name')
      const routePath = stringProperty(node, 'path')
      if (name && routePath !== null) {
        routes.set(name, routePath.startsWith('/') ? routePath : `/${routePath}`)
      }
    }
    ts.forEachChild(node, visit)
  }
  visit(sourceFile)
  return routes
}

function collectMarkers(sourceText) {
  const markers = new Set()
  const pattern = /data-ai-targets?="([^"]+)"/g
  for (const match of sourceText.matchAll(pattern)) {
    for (const targetKey of match[1].trim().split(/\s+/)) {
      if (targetKey) markers.add(targetKey)
    }
  }
  return markers
}

function collectVueFiles(directory) {
  const files = []
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const entryPath = path.join(directory, entry.name)
    if (entry.isDirectory()) files.push(...collectVueFiles(entryPath))
    else if (entry.isFile() && entry.name.endsWith('.vue')) files.push(entryPath)
  }
  return files
}

function validateContract() {
  const contract = readJson(contractPath)
  const routes = collectNamedRoutes(fs.readFileSync(routerPath, 'utf8'))
  const errors = []
  const targetKeys = new Set()
  const guidanceTypes = new Set(contract.guidance_business_types || [])

  if (contract.version !== 1) {
    errors.push(`不支持的契约版本：${String(contract.version)}`)
  }

  for (const capability of contract.capabilities || []) {
    const targetKey = capability.target_key
    if (!targetKey || targetKeys.has(targetKey)) {
      errors.push(`target_key 缺失或重复：${String(targetKey)}`)
      continue
    }
    targetKeys.add(targetKey)

    for (const businessType of capability.business_types || []) {
      if (!guidanceTypes.has(businessType)) {
        errors.push(`${targetKey} 使用了未登记业务类型：${businessType}`)
      }
    }

    if (!Array.isArray(capability.routes) || capability.routes.length === 0) {
      errors.push(`${targetKey} 未声明可到达路由`)
      continue
    }

    for (const route of capability.routes) {
      const actualPath = routes.get(route.name)
      if (!actualPath) {
        errors.push(`${targetKey} 指向不存在的路由：${route.name}`)
      } else if (actualPath !== route.path) {
        errors.push(
          `${targetKey} 路由路径漂移：${route.name} 应为 ${route.path}，实际为 ${actualPath}`,
        )
      }

      const markerFiles = route.marker_files || []
      const markerFound = markerFiles.some((relativeFile) => {
        const absoluteFile = path.resolve(repositoryRoot, relativeFile)
        const isInsideRepository = path.relative(repositoryRoot, absoluteFile)
        if (isInsideRepository.startsWith('..') || path.isAbsolute(isInsideRepository)) {
          errors.push(`${targetKey} 的控件文件越出项目目录：${relativeFile}`)
          return false
        }
        if (!fs.existsSync(absoluteFile)) {
          errors.push(`${targetKey} 的控件文件不存在：${relativeFile}`)
          return false
        }
        return collectMarkers(fs.readFileSync(absoluteFile, 'utf8')).has(targetKey)
      })
      if (!markerFound) {
        errors.push(`${targetKey} 在路由 ${route.name} 中缺少 data-ai-target 标记`)
      }
    }
  }

  for (const vueFile of collectVueFiles(path.join(frontendRoot, 'src'))) {
    for (const marker of collectMarkers(fs.readFileSync(vueFile, 'utf8'))) {
      if (!targetKeys.has(marker)) {
        errors.push(
          `前端存在未登记的 AI 控件：${marker}（${path.relative(repositoryRoot, vueFile)}）`,
        )
      }
    }
  }

  if (errors.length > 0) {
    for (const error of errors) console.error(`- ${error}`)
    process.exitCode = 1
    return
  }

  console.log(
    `AI 页面能力契约校验通过：${targetKeys.size} 个控件，${routes.size} 个命名路由`,
  )
}

validateContract()
