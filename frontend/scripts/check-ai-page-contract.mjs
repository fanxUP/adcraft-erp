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
const permissionPath = path.join(repositoryRoot, 'backend/app/core/permissions.py')
const pageCapabilityDirectory = path.join(frontendRoot, 'src/config/page-capabilities')

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

function collectConfiguredPages() {
  const pages = new Map()
  for (const fileName of fs.readdirSync(pageCapabilityDirectory)) {
    if (!fileName.endsWith('.ts')) continue
    const filePath = path.join(pageCapabilityDirectory, fileName)
    const sourceFile = ts.createSourceFile(
      filePath,
      fs.readFileSync(filePath, 'utf8'),
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TS,
    )
    const visit = (node) => {
      if (ts.isObjectLiteralExpression(node)) {
        for (const property of node.properties) {
          if (
            !ts.isPropertyAssignment(property)
            || !ts.isObjectLiteralExpression(property.initializer)
          ) continue
          const title = stringProperty(property.initializer, 'title')
          const purpose = stringProperty(property.initializer, 'purpose')
          const workflowStage = stringProperty(property.initializer, 'workflowStage')
          if (!title || !purpose || !workflowStage) continue
          const pageKey = property.name.getText().replace(/^['"]|['"]$/g, '')
          pages.set(pageKey, { title, purpose, workflowStage })
        }
      }
      ts.forEachChild(node, visit)
    }
    visit(sourceFile)
  }
  return pages
}

function collectPermissionCodes(sourceText) {
  const codes = new Set()
  const pattern = /^PERM_[A-Z0-9_]+\s*=\s*["']([^"']+)["']/gm
  for (const match of sourceText.matchAll(pattern)) codes.add(match[1])
  return codes
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
  const configuredPages = collectConfiguredPages()
  const permissionCodes = collectPermissionCodes(
    fs.readFileSync(permissionPath, 'utf8'),
  )
  const errors = []
  const targetKeys = new Set()
  const guidanceTypes = new Set(contract.guidance_business_types || [])
  const semantics = contract.semantics || {}

  if (contract.version !== 2) {
    errors.push(`不支持的契约版本：${String(contract.version)}`)
  }

  const pageKeys = new Set()
  for (const page of contract.pages || []) {
    if (!page.page_key || pageKeys.has(page.page_key)) {
      errors.push(`page_key 缺失或重复：${String(page.page_key)}`)
      continue
    }
    pageKeys.add(page.page_key)
    const actualPath = routes.get(page.route_name)
    if (!actualPath) {
      errors.push(`${page.page_key} 指向不存在的页面路由：${page.route_name}`)
    } else if (actualPath !== page.path) {
      errors.push(
        `${page.page_key} 页面路径漂移：应为 ${page.path}，实际为 ${actualPath}`,
      )
    }
    const configured = configuredPages.get(page.page_key)
    if (!configured) {
      errors.push(`${page.page_key} 缺少前端页面说明`)
    } else {
      const expected = {
        title: page.title,
        purpose: page.purpose,
        workflowStage: page.workflow_stage,
      }
      for (const [field, value] of Object.entries(expected)) {
        if (configured[field] !== value) {
          errors.push(
            `${page.page_key} 的 ${field} 与契约不一致：${configured[field]} != ${value}`,
          )
        }
      }
    }
    for (const businessType of page.business_types || []) {
      if (!guidanceTypes.has(businessType)) {
        errors.push(`${page.page_key} 使用了未登记业务类型：${businessType}`)
      }
    }
  }

  for (const capability of contract.capabilities || []) {
    const targetKey = capability.target_key
    if (!targetKey || targetKeys.has(targetKey)) {
      errors.push(`target_key 缺失或重复：${String(targetKey)}`)
      continue
    }
    targetKeys.add(targetKey)
    const operation = semantics[targetKey]
    if (!operation) {
      errors.push(`${targetKey} 缺少操作语义`)
      continue
    }
    const requiredTextFields = ['purpose', 'completion_signal']
    for (const field of requiredTextFields) {
      if (typeof operation[field] !== 'string' || !operation[field].trim()) {
        errors.push(`${targetKey} 的 ${field} 不能为空`)
      }
    }
    for (const field of ['prerequisites', 'blocking_conditions']) {
      if (
        !Array.isArray(operation[field])
        || operation[field].length === 0
        || !operation[field].every(item => typeof item === 'string' && item.trim())
      ) {
        errors.push(`${targetKey} 的 ${field} 必须是非空文本数组`)
      }
    }
    if (!['read', 'write'].includes(operation.effect)) {
      errors.push(`${targetKey} 的 effect 必须是 read 或 write`)
    }
    if (operation.effect === 'write' && operation.requires_confirmation !== true) {
      errors.push(`${targetKey} 是写操作但未要求人工确认`)
    }

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
      const requiredPermission = operation.required_permissions?.[route.name]
      if (!requiredPermission) {
        errors.push(`${targetKey} 在 ${route.name} 缺少 required_permission`)
      } else if (!permissionCodes.has(requiredPermission)) {
        errors.push(`${targetKey} 使用了未登记权限：${requiredPermission}`)
      }
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

  for (const semanticKey of Object.keys(semantics)) {
    if (!targetKeys.has(semanticKey)) {
      errors.push(`存在无控件对应的操作语义：${semanticKey}`)
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
    `AI 页面能力契约校验通过：${pageKeys.size} 个页面，`
    + `${targetKeys.size} 个语义控件，${routes.size} 个命名路由`,
  )
}

validateContract()
