import { describe, expect, it } from 'vitest'
import {
  INSTALLATION_MEDIA_MAX_BATCH,
  INSTALLATION_PHOTO_MAX_BYTES,
  INSTALLATION_PHOTO_PREVIEW_ZOOM_RATE,
  INSTALLATION_VIDEO_MAX_BYTES,
  TASK_ATTACHMENT_ACCEPT,
  TASK_ATTACHMENT_FILE_MAX_BYTES,
  TASK_ATTACHMENT_IMAGE_MAX_BYTES,
  TASK_ATTACHMENT_PREVIEW_ZOOM_RATE,
  formatAttachmentSize,
  getAttachmentUrl,
  getTaskAttachmentKind,
  isInstallationMediaAttachment,
  isInstallationVideoAttachment,
  isInstallationPhotoAttachment,
  validateTaskAttachment,
  validateInstallationMedia,
  validateInstallationPhoto,
} from './taskPhotoUpload'
import { groupAttachmentsByDate, groupAttachmentsByItemAndDate } from './orderAttachmentAlbum'

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

  it('validates common task attachment formats and exposes conservative limits', () => {
    expect(validateTaskAttachment({ name: '设计.jpg', type: 'image/jpeg', size: 1024 })).toBeNull()
    expect(validateTaskAttachment({ name: '说明.pdf', type: 'application/pdf', size: 1024 })).toBeNull()
    expect(validateTaskAttachment({ name: '清单.xlsx', type: '', size: 1024 })).toBeNull()
    expect(validateTaskAttachment({ name: '图纸.dwg', type: 'application/octet-stream', size: 1024 })).toBeNull()
    expect(validateTaskAttachment({ name: '现场.mp4', type: 'video/mp4', size: 1024 })).toBeNull()
    expect(validateTaskAttachment({ name: '脚本.html', type: 'text/html', size: 1024 })).toContain('支持')
    expect(validateTaskAttachment({ name: '大图.png', type: 'image/png', size: TASK_ATTACHMENT_IMAGE_MAX_BYTES + 1 })).toContain('10MB')
    expect(validateTaskAttachment({ name: '大文件.zip', type: 'application/zip', size: TASK_ATTACHMENT_FILE_MAX_BYTES + 1 })).toContain('45MB')
    expect(TASK_ATTACHMENT_ACCEPT).toContain('.dwg')
    expect(TASK_ATTACHMENT_PREVIEW_ZOOM_RATE).toBe(1.05)
  })

  it('classifies non-image attachments without requiring thumbnails', () => {
    expect(getTaskAttachmentKind({ filename: '方案.pdf', file_type: 'application/pdf' })).toBe('pdf')
    expect(getTaskAttachmentKind({ filename: '现场.mp4', file_type: 'video/mp4' })).toBe('video')
    expect(getTaskAttachmentKind({ filename: '图纸.dwg', file_type: 'application/octet-stream' })).toBe('cad')
    expect(getTaskAttachmentKind({ filename: '资料.zip', file_type: 'application/zip' })).toBe('archive')
    expect(getTaskAttachmentKind({ filename: '旧文件.bin', file_type: 'application/octet-stream' })).toBe('file')
    expect(formatAttachmentSize(1024)).toBe('1.0 KB')
    expect(formatAttachmentSize(1024 * 1024)).toBe('1.0 MB')
  })

  it('groups attachments by server upload date in descending order', () => {
    const groups = groupAttachmentsByDate([
      { id: 'older', created_at: '2026-09-13T08:00:00+08:00' },
      { id: 'newer', created_at: '2026-09-14T16:20:00+08:00' },
      { id: 'same-day-later', created_at: '2026-09-14T18:20:00+08:00' },
      { id: 'unknown', created_at: null },
    ])

    expect(groups.map(group => group.label)).toEqual([
      '2026-09-14',
      '2026-09-13',
      '时间未知',
    ])
    expect(groups[0].attachments.map(item => item.id)).toEqual([
      'same-day-later',
      'newer',
    ])
    expect(groups[2].isUnknown).toBe(true)
  })

  it('groups materials by order item first and then by upload date', () => {
    const groups = groupAttachmentsByItemAndDate([
      { id: 'item-a-old', order_item_id: 'item-a', order_item_name: '标志', order_item_sort_order: 0, created_at: '2026-09-13T08:00:00+08:00' },
      { id: 'item-b-new', order_item_id: 'item-b', order_item_name: '发光字', order_item_sort_order: 1, created_at: '2026-09-14T16:20:00+08:00' },
      { id: 'item-a-new', order_item_id: 'item-a', order_item_name: '标志', order_item_sort_order: 0, created_at: '2026-09-14T18:20:00+08:00' },
      { id: 'unscoped', order_item_id: null, created_at: null },
    ])

    expect(groups.map(group => group.label)).toEqual(['标志', '发光字', '未关联项目内容'])
    expect(groups[0].dates.map(date => date.label)).toEqual(['2026-09-14', '2026-09-13'])
    expect(groups[0].dates[0].attachments.map(item => item.id)).toEqual(['item-a-new'])
    expect(groups[2].orderItemId).toBeNull()
  })
})
