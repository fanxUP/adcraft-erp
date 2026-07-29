import { describe, expect, it } from 'vitest'
import type { AiPageActionGuide } from '@/types/aiAssistant'
import {
  loadPersistedPageGuide,
  persistPageGuide,
} from './pageGuidePersistence'

class MemoryStorage implements Storage {
  private values = new Map<string, string>()

  get length() {
    return this.values.size
  }

  clear() {
    this.values.clear()
  }

  getItem(key: string) {
    return this.values.get(key) ?? null
  }

  key(index: number) {
    return [...this.values.keys()][index] ?? null
  }

  removeItem(key: string) {
    this.values.delete(key)
  }

  setItem(key: string, value: string) {
    this.values.set(key, value)
  }
}

const guide: AiPageActionGuide = {
  label: '进入生产阶段',
  target_path: '/orders/33333333-3333-3333-3333-333333333333',
  target_key: 'order-status-in_production',
  target_status: 'in_production',
}

describe('page guide persistence', () => {
  it('restores a valid guide only for its owner', () => {
    const storage = new MemoryStorage()
    persistPageGuide(storage, 'user-a', guide, 1_000)

    expect(loadPersistedPageGuide(storage, 'user-a', 2_000)).toEqual(guide)
    expect(loadPersistedPageGuide(storage, 'user-b', 2_000)).toBeNull()
  })

  it('removes an expired guide instead of restoring it', () => {
    const storage = new MemoryStorage()
    persistPageGuide(storage, 'user-a', guide, 1_000, 500)

    expect(loadPersistedPageGuide(storage, 'user-a', 1_501)).toBeNull()
    expect(storage.length).toBe(0)
  })

  it('restores a strictly parsed installation form draft', () => {
    const storage = new MemoryStorage()
    const draftGuide: AiPageActionGuide = {
      label: '预览安装准备草稿',
      target_path: '/installation-tasks/44444444-4444-4444-4444-444444444444',
      target_key: 'installation-draft',
      draft: {
        kind: 'installation_task_update',
        title: '安装准备信息草稿',
        fields: [
          {
            key: 'address',
            label: '安装地址',
            value: '上海市静安区测试路 88 号',
            source: 'order',
            hint: '来自订单安装地址，请现场确认',
          },
        ],
      },
    }
    persistPageGuide(storage, 'user-a', draftGuide, 1_000)

    expect(loadPersistedPageGuide(storage, 'user-a', 2_000)).toEqual(draftGuide)
  })

  it('removes malformed or unsafe persisted data', () => {
    const storage = new MemoryStorage()
    storage.setItem('adcraft-ai-page-guide:v1:user-a', JSON.stringify({
      version: 1,
      expires_at: 20_000,
      guide: {
        ...guide,
        target_path: 'https://unsafe.example/orders/1',
      },
    }))

    expect(loadPersistedPageGuide(storage, 'user-a', 2_000)).toBeNull()
    expect(storage.length).toBe(0)
  })

  it('never blocks guidance when browser storage is unavailable', () => {
    const storage = {
      getItem: () => { throw new Error('storage disabled') },
      setItem: () => { throw new Error('storage disabled') },
      removeItem: () => { throw new Error('storage disabled') },
    } as unknown as Storage

    expect(() => persistPageGuide(storage, 'user-a', guide)).not.toThrow()
    expect(loadPersistedPageGuide(storage, 'user-a')).toBeNull()
  })
})
