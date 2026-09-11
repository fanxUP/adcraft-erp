export const PROJECT_COST_ATTACHMENT_ACCEPT = 'image/jpeg,image/png,image/webp,.pdf'
export const PROJECT_COST_ATTACHMENT_PREVIEW_ZOOM_RATE = 1.05

export type ProjectCostAttachmentKind = 'image' | 'pdf' | 'file'

type ProjectCostAttachmentLike = {
  filename?: string | null
  file_type?: string | null
}

type ProjectCostAttachmentFileLike = ProjectCostAttachmentLike & {
  name?: string | null
  type?: string | null
}

const IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])
const IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp'])

function getExtension(filename?: string | null): string {
  const match = filename?.trim().toLowerCase().match(/\.[a-z0-9]+$/)
  return match?.[0] || ''
}

export function getProjectCostAttachmentKind(attachment: ProjectCostAttachmentLike): ProjectCostAttachmentKind {
  const fileType = attachment.file_type?.trim().toLowerCase() || ''
  const extension = getExtension(attachment.filename)
  if (fileType.startsWith('image/') || IMAGE_EXTENSIONS.has(extension)) return 'image'
  if (fileType === 'application/pdf' || extension === '.pdf') return 'pdf'
  return 'file'
}

export function validateProjectCostAttachment(file: ProjectCostAttachmentFileLike): string | null {
  const fileType = file.type?.trim().toLowerCase() || ''
  const extension = getExtension(file.name)
  const supportedByType = IMAGE_TYPES.has(fileType) || fileType === 'application/pdf'
  const supportedByExtension = IMAGE_EXTENSIONS.has(extension) || extension === '.pdf'

  // Some browsers do not provide a MIME type for dragged files, so the extension
  // is a safe fallback for the picker/dropzone UI validation.
  if (fileType ? !supportedByType : !supportedByExtension) {
    return '凭证仅支持 JPG、PNG、WEBP 或 PDF 文件'
  }
  return null
}

export function getProjectCostAttachmentUrl(filePath: string): string {
  if (!filePath) return ''
  return filePath.startsWith('/') ? filePath : `/uploads/${filePath}`
}
