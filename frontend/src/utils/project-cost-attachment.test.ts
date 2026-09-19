import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  getProjectCostAttachmentKind,
  validateProjectCostAttachment,
} from './projectCostAttachment'

const srcRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function readSource(relativePath: string) {
  return readFileSync(resolve(srcRoot, relativePath), 'utf8')
}

describe('登记成本凭证上传交互', () => {
  it('使用可拖拽的凭证上传区域并支持批量拖入', () => {
    const source = readSource('views/payments/ProjectCostDetail.vue')

    expect(source).toContain('class="cost-attachment-dropzone"')
    expect(source).toContain('@drop.prevent="handleCostAttachmentDrop"')
    expect(source).toContain('@change="handleCostAttachmentInputChange"')
    expect(source).toContain('PROJECT_COST_ATTACHMENT_ACCEPT')
    expect(source).toContain('validateProjectCostAttachment')
  })

  it('图片凭证使用可缩放的图片预览器，非图片保持文件卡片', () => {
    const source = readSource('views/payments/ProjectCostDetail.vue')

    expect(source).toContain(':preview-src-list="imageAttachmentUrls"')
    expect(source).toContain(':zoom-rate="PROJECT_COST_ATTACHMENT_PREVIEW_ZOOM_RATE"')
    expect(source).toContain('preview-teleported')
    expect(source).toContain('getProjectCostAttachmentKind(att)')
    expect(source).toContain('previewCostAttachment(att)')
  })

  it('只接受 JPG、PNG、WEBP 和 PDF，并按附件类型区分图片预览', () => {
    expect(validateProjectCostAttachment({ name: '现场.jpg', type: 'image/jpeg' })).toBeNull()
    expect(validateProjectCostAttachment({ name: '凭证.pdf', type: 'application/pdf' })).toBeNull()
    expect(validateProjectCostAttachment({ name: '拖拽图片.webp', type: '' })).toBeNull()
    expect(validateProjectCostAttachment({ name: '凭证.gif', type: 'image/gif' })).toContain('仅支持')

    expect(getProjectCostAttachmentKind({ filename: 'a.png', file_type: 'image/png' })).toBe('image')
    expect(getProjectCostAttachmentKind({ filename: 'a.pdf', file_type: 'application/pdf' })).toBe('pdf')
    expect(getProjectCostAttachmentKind({ filename: 'a.bin', file_type: 'application/octet-stream' })).toBe('file')
  })

  it('新登记成本可以先排队凭证，保存成本后自动上传', () => {
    const source = readSource('views/payments/ProjectCostDetail.vue')

    expect(source).toContain("保存成本后自动上传")
    expect(source).toContain("const costId = editingId.value")
    expect(source).toContain("item.status === 'queued' && (!item.costId || item.costId === costId)")
    expect(source).toContain('let savedCost: ProjectCostResponse')
    expect(source).toContain('await startCostAttachmentUploadQueue()')
  })
})
