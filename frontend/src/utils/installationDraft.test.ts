import { describe, expect, it } from 'vitest'
import { applyInstallationDraft } from './installationDraft'

describe('installation draft helper', () => {
  it('applies only non-empty safe suggestions to the local form', () => {
    const form = {
      assigned_to: '',
      address: '',
      scheduled_at: '',
      contact_name: '王师傅',
    }

    const applied = applyInstallationDraft(form, {
      kind: 'installation_task_update',
      title: '安装准备信息草稿',
      fields: [
        {
          key: 'assigned_to',
          label: '负责人',
          value: null,
          source: 'manual',
          hint: '请选择负责人',
        },
        {
          key: 'address',
          label: '安装地址',
          value: '上海市静安区测试路 88 号',
          source: 'order',
          hint: '来自订单安装地址',
        },
        {
          key: 'scheduled_at',
          label: '计划安装时间',
          value: '2026-08-02T14:30:00+08:00',
          source: 'order',
          hint: '参考订单交付期限',
        },
      ],
    })

    expect(applied).toEqual(['address', 'scheduled_at'])
    expect(form).toEqual({
      assigned_to: '',
      address: '上海市静安区测试路 88 号',
      scheduled_at: '2026-08-02T14:30:00',
      contact_name: '王师傅',
    })
  })
})
