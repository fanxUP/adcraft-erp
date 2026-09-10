export const INSTALLATION_PHOTO_MAX_BYTES = 10 * 1024 * 1024
export const INSTALLATION_PHOTO_ACCEPT = 'image/jpeg,image/png,image/webp'
export const INSTALLATION_VIDEO_MAX_BYTES = 45 * 1024 * 1024
export const INSTALLATION_VIDEO_ACCEPT = 'video/mp4,video/webm,video/quicktime'
export const INSTALLATION_MEDIA_ACCEPT = `${INSTALLATION_PHOTO_ACCEPT},${INSTALLATION_VIDEO_ACCEPT}`
export const INSTALLATION_MEDIA_MAX_BATCH = 20
// Keep the old name for callers that still use the photo-only terminology.
export const INSTALLATION_PHOTO_MAX_BATCH = INSTALLATION_MEDIA_MAX_BATCH
// Element Plus defaults to 1.2 (20% per wheel step), which is too aggressive
// for detailed site-photo inspection. Keep the step small and easy to tune.
export const INSTALLATION_PHOTO_PREVIEW_ZOOM_RATE = 1.05

export const TASK_ATTACHMENT_IMAGE_MAX_BYTES = 10 * 1024 * 1024
export const TASK_ATTACHMENT_FILE_MAX_BYTES = 45 * 1024 * 1024
export const TASK_ATTACHMENT_MAX_BATCH = 20
export const TASK_ATTACHMENT_MAX_CONCURRENCY = 3
export const TASK_ATTACHMENT_PREVIEW_ZOOM_RATE = 1.05
export const TASK_ATTACHMENT_ACCEPT = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'video/mp4',
  'video/webm',
  'video/quicktime',
  'application/pdf',
  '.jpg',
  '.jpeg',
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
  '.dwg',
  '.dxf',
  '.zip',
  '.rar',
  '.7z',
].join(',')

type PhotoFileLike = {
  name?: string
  type?: string
  size?: number
}

type PhotoAttachmentLike = {
  category?: string | null
  file_type?: string | null
}

export type TaskAttachmentKind = 'image' | 'video' | 'pdf' | 'document' | 'cad' | 'archive' | 'file'

type TaskAttachmentLike = PhotoAttachmentLike & {
  filename?: string | null
}

const INSTALLATION_VIDEO_TYPES = new Set(['video/mp4', 'video/webm', 'video/quicktime'])

export function validateInstallationPhoto(file: PhotoFileLike): string | null {
  const supportedTypes = new Set(['image/jpeg', 'image/png', 'image/webp'])
  if (!file.type || !supportedTypes.has(file.type)) {
    return '现场照片仅支持 JPG、PNG 或 WEBP 图片'
  }
  if (typeof file.size === 'number' && file.size > INSTALLATION_PHOTO_MAX_BYTES) {
    return '单张现场照片不能超过 10MB'
  }
  return null
}

export function validateInstallationMedia(file: PhotoFileLike): string | null {
  if (file.type?.startsWith('image/')) {
    return validateInstallationPhoto(file)
  }
  if (!file.type || !INSTALLATION_VIDEO_TYPES.has(file.type)) {
    return '现场媒体仅支持 JPG、PNG、WEBP、MP4、WEBM 或 MOV 文件'
  }
  if (typeof file.size === 'number' && file.size > INSTALLATION_VIDEO_MAX_BYTES) {
    return '单个现场视频不能超过 45MB'
  }
  return null
}

export function isInstallationPhotoAttachment(att: PhotoAttachmentLike): boolean {
  return Boolean(att.file_type?.startsWith('image/')) || (att.category === 'photo' && !att.file_type)
}

export function isInstallationVideoAttachment(att: PhotoAttachmentLike): boolean {
  return Boolean(att.file_type?.startsWith('video/')) || att.category === 'video'
}

export function isInstallationMediaAttachment(att: PhotoAttachmentLike): boolean {
  return isInstallationPhotoAttachment(att) || isInstallationVideoAttachment(att)
}

export function getAttachmentUrl(filePath: string): string {
  if (!filePath) return ''
  return filePath.startsWith('/') ? filePath : `/uploads/${filePath}`
}

const TASK_ATTACHMENT_IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp'])
const TASK_ATTACHMENT_VIDEO_EXTENSIONS = new Set(['.mp4', '.webm', '.mov'])
const TASK_ATTACHMENT_DOCUMENT_EXTENSIONS = new Set(['.doc', '.docx', '.xls', '.xlsx'])
const TASK_ATTACHMENT_CAD_EXTENSIONS = new Set(['.dwg', '.dxf'])
const TASK_ATTACHMENT_ARCHIVE_EXTENSIONS = new Set(['.zip', '.rar', '.7z'])
const TASK_ATTACHMENT_IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])
const TASK_ATTACHMENT_VIDEO_TYPES = new Set(['video/mp4', 'video/webm', 'video/quicktime'])

function getAttachmentExtension(filename?: string | null): string {
  const match = filename?.trim().toLowerCase().match(/\.[a-z0-9]+$/)
  return match?.[0] || ''
}

export function getTaskAttachmentKind(attachment: TaskAttachmentLike): TaskAttachmentKind {
  const fileType = attachment.file_type?.toLowerCase() || ''
  const extension = getAttachmentExtension(attachment.filename)
  if (fileType.startsWith('image/') || attachment.category === 'image' || TASK_ATTACHMENT_IMAGE_EXTENSIONS.has(extension)) return 'image'
  if (fileType.startsWith('video/') || attachment.category === 'video' || TASK_ATTACHMENT_VIDEO_EXTENSIONS.has(extension)) return 'video'
  if (fileType === 'application/pdf' || attachment.category === 'pdf' || extension === '.pdf') return 'pdf'
  if (attachment.category === 'document' || TASK_ATTACHMENT_DOCUMENT_EXTENSIONS.has(extension) || fileType.includes('word') || fileType.includes('excel') || fileType.includes('spreadsheetml') || fileType.includes('wordprocessingml')) return 'document'
  if (attachment.category === 'cad' || TASK_ATTACHMENT_CAD_EXTENSIONS.has(extension) || fileType.includes('dwg') || fileType.includes('dxf') || fileType.includes('acad')) return 'cad'
  if (attachment.category === 'archive' || TASK_ATTACHMENT_ARCHIVE_EXTENSIONS.has(extension) || fileType.includes('zip') || fileType.includes('rar') || fileType.includes('7z')) return 'archive'
  return 'file'
}

export function getTaskAttachmentTypeLabel(attachment: TaskAttachmentLike): string {
  const labels: Record<TaskAttachmentKind, string> = {
    image: '图片',
    video: '视频',
    pdf: 'PDF',
    document: '文档',
    cad: 'CAD 图纸',
    archive: '压缩包',
    file: '文件',
  }
  return labels[getTaskAttachmentKind(attachment)]
}

export function validateTaskAttachment(file: PhotoFileLike): string | null {
  const kind = getTaskAttachmentKind({ filename: file.name, file_type: file.type })
  if (kind === 'file') return '任务附件仅支持 JPG、PNG、WEBP、视频、PDF、Word、Excel、CAD 或压缩包'

  const fileType = file.type?.toLowerCase() || ''
  if (kind === 'image' && fileType && !TASK_ATTACHMENT_IMAGE_TYPES.has(fileType)) {
    return '图片仅支持 JPG、PNG 或 WEBP 格式'
  }
  if (kind === 'video' && fileType && !TASK_ATTACHMENT_VIDEO_TYPES.has(fileType)) {
    return '视频仅支持 MP4、WEBM 或 MOV 格式'
  }
  if (typeof file.size === 'number') {
    const maxBytes = kind === 'image' ? TASK_ATTACHMENT_IMAGE_MAX_BYTES : TASK_ATTACHMENT_FILE_MAX_BYTES
    if (file.size > maxBytes) return `${kind === 'image' ? '图片' : '附件'}不能超过 ${kind === 'image' ? '10MB' : '45MB'}`
  }
  return null
}

export function formatAttachmentSize(size?: number | null): string {
  if (!size || size < 0) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`
  return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`
}
