import { describe, expect, it } from 'vitest'
import {
  INSTALLATION_PHOTO_MAX_BYTES,
  INSTALLATION_PHOTO_PREVIEW_ZOOM_RATE,
  getAttachmentUrl,
  isInstallationPhotoAttachment,
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

  it('rejects unsupported formats and oversized images with plain-language messages', () => {
    expect(validateInstallationPhoto({ name: '说明.pdf', type: 'application/pdf', size: 1024 })).toContain('JPG')
    expect(validateInstallationPhoto({ name: '现场.jpg', type: 'image/jpeg', size: INSTALLATION_PHOTO_MAX_BYTES + 1 })).toContain('10MB')
  })

  it('keeps historical image attachments visible even when category is missing', () => {
    expect(isInstallationPhotoAttachment({ category: 'photo', file_type: 'application/octet-stream' })).toBe(false)
    expect(isInstallationPhotoAttachment({ category: 'photo', file_type: null })).toBe(true)
    expect(isInstallationPhotoAttachment({ category: null, file_type: 'image/jpeg' })).toBe(true)
    expect(isInstallationPhotoAttachment({ category: null, file_type: 'application/pdf' })).toBe(false)
  })

  it('normalizes relative attachment paths for the uploads mount', () => {
    expect(getAttachmentUrl('202609/photo.jpg')).toBe('/uploads/202609/photo.jpg')
    expect(getAttachmentUrl('/uploads/202609/photo.jpg')).toBe('/uploads/202609/photo.jpg')
  })
})
