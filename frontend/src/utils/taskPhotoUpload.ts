export const INSTALLATION_PHOTO_MAX_BYTES = 10 * 1024 * 1024
export const INSTALLATION_PHOTO_ACCEPT = 'image/jpeg,image/png,image/webp'
export const INSTALLATION_PHOTO_MAX_BATCH = 20
// Element Plus defaults to 1.2 (20% per wheel step), which is too aggressive
// for detailed site-photo inspection. Keep the step small and easy to tune.
export const INSTALLATION_PHOTO_PREVIEW_ZOOM_RATE = 1.05

type PhotoFileLike = {
  name?: string
  type?: string
  size?: number
}

type PhotoAttachmentLike = {
  category?: string | null
  file_type?: string | null
}

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

export function isInstallationPhotoAttachment(att: PhotoAttachmentLike): boolean {
  return Boolean(att.file_type?.startsWith('image/')) || (att.category === 'photo' && !att.file_type)
}

export function getAttachmentUrl(filePath: string): string {
  if (!filePath) return ''
  return filePath.startsWith('/') ? filePath : `/uploads/${filePath}`
}
