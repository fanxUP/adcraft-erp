import { describe, expect, it } from 'vitest'
import {
  INSTALLATION_MEDIA_MAX_BATCH,
  INSTALLATION_PHOTO_MAX_BYTES,
  INSTALLATION_PHOTO_PREVIEW_ZOOM_RATE,
  INSTALLATION_VIDEO_MAX_BYTES,
  getAttachmentUrl,
  isInstallationMediaAttachment,
  isInstallationVideoAttachment,
  isInstallationPhotoAttachment,
  validateInstallationMedia,
  validateInstallationPhoto,
} from './taskPhotoUpload'

describe('task photo upload helpers', () => {
  it('uses a gentle wheel zoom step for site photo previews', () => {
    expect(INSTALLATION_PHOTO_PREVIEW_ZOOM_RATE).toBe(1.05)
    expect(INSTALLATION_PHOTO_PREVIEW_ZOOM_RATE).toBeLessThan(1.2)
  })

  it('accepts supported image files below the size limit', () => {
    expect(validateInstallationPhoto({ name: '现场.jpg', type: 'image/jpeg', size: 1024 })).toBeNull()
    expect(validateInstallationPhoto({ name: '现场.png', type: 'image/png', size: INSTALLATION_PHOTO_MAX_BYTES })).toBeNull()
    expect(validateInstallationPhoto({ name: '现场.webp', type: 'image/webp', size: 1024 })).toBeNull()
  })

  it('accepts supported video files below the video size limit', () => {
    expect(validateInstallationMedia({ name: '现场.mp4', type: 'video/mp4', size: 1024 })).toBeNull()
    expect(validateInstallationMedia({ name: '现场.webm', type: 'video/webm', size: INSTALLATION_VIDEO_MAX_BYTES })).toBeNull()
    expect(validateInstallationMedia({ name: '现场.mov', type: 'video/quicktime', size: 1024 })).toBeNull()
    expect(INSTALLATION_MEDIA_MAX_BATCH).toBe(20)
  })

  it('rejects unsupported formats and oversized images with plain-language messages', () => {
    expect(validateInstallationPhoto({ name: '说明.pdf', type: 'application/pdf', size: 1024 })).toContain('JPG')
    expect(validateInstallationPhoto({ name: '现场.jpg', type: 'image/jpeg', size: INSTALLATION_PHOTO_MAX_BYTES + 1 })).toContain('10MB')
    expect(validateInstallationMedia({ name: '说明.pdf', type: 'application/pdf', size: 1024 })).toContain('MP4')
    expect(validateInstallationMedia({ name: '现场.mp4', type: 'video/mp4', size: INSTALLATION_VIDEO_MAX_BYTES + 1 })).toContain('45MB')
  })

  it('keeps historical image attachments visible even when category is missing', () => {
    expect(isInstallationPhotoAttachment({ category: 'photo', file_type: 'application/octet-stream' })).toBe(false)
    expect(isInstallationPhotoAttachment({ category: 'photo', file_type: null })).toBe(true)
    expect(isInstallationPhotoAttachment({ category: null, file_type: 'image/jpeg' })).toBe(true)
    expect(isInstallationPhotoAttachment({ category: null, file_type: 'application/pdf' })).toBe(false)
  })

  it('recognizes installation videos and combines them with photos as media', () => {
    const video = { category: 'video', file_type: 'video/mp4' }
    expect(isInstallationVideoAttachment(video)).toBe(true)
    expect(isInstallationMediaAttachment(video)).toBe(true)
    expect(isInstallationMediaAttachment({ category: 'file', file_type: 'application/pdf' })).toBe(false)
  })

  it('normalizes relative attachment paths for the uploads mount', () => {
    expect(getAttachmentUrl('202609/photo.jpg')).toBe('/uploads/202609/photo.jpg')
    expect(getAttachmentUrl('/uploads/202609/photo.jpg')).toBe('/uploads/202609/photo.jpg')
  })
})
