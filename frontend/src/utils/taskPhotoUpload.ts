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

type PhotoFileLike = {
  name?: string
  type?: string
  size?: number
}

type PhotoAttachmentLike = {
  category?: string | null
  file_type?: string | null
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
