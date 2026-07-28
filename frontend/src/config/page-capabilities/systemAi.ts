import type { PageCapabilityMap } from './types'

export const systemAiCapabilities: PageCapabilityMap = {
  notifications: {
    title: '消息中心',
    purpose: '查看系统提醒和业务待办通知',
    workflowStage: 'communication',
    availableActions: ['查看通知', '标记已读', '进入相关业务'],
  },
  chat: {
    title: '即时通讯',
    purpose: '与同事沟通项目、任务和日常工作',
    workflowStage: 'communication',
    availableActions: ['发起会话', '发送消息', '搜索消息'],
  },
  admin_users: {
    title: '用户管理',
    purpose: '维护系统账号、状态和角色分配',
    workflowStage: 'administration',
    availableActions: ['查询用户', '新增用户', '分配角色'],
  },
  admin_roles: {
    title: '角色权限',
    purpose: '维护角色及其可访问的系统权限',
    workflowStage: 'administration',
    availableActions: ['查看角色', '调整权限', '查看用户分配'],
  },
  admin_settings: {
    title: '系统设置',
    purpose: '维护系统级业务参数和运行配置',
    workflowStage: 'administration',
    availableActions: ['查看配置', '调整配置', '保存设置'],
  },
  ai_providers: {
    title: 'AI 模型中心',
    purpose: '配置 AI 服务商、模型、路由和连接状态',
    workflowStage: 'ai_administration',
    availableActions: ['查看模型配置', '测试连接', '调整模型路由'],
  },
  operation_logs: {
    title: '操作日志',
    purpose: '审计用户对关键业务数据的操作记录',
    workflowStage: 'administration',
    availableActions: ['查询日志', '按用户筛选', '按业务筛选'],
  },
  backups: {
    title: '备份管理',
    purpose: '查看、创建和恢复系统数据备份',
    workflowStage: 'administration',
    availableActions: ['查看备份', '创建备份', '按权限恢复'],
  },
  anomaly_dashboard: {
    title: '智能异常提醒',
    purpose: '集中查看订单、收款、外协和库存异常',
    workflowStage: 'ai_analysis',
    availableActions: ['查看异常', '筛选异常类型', '进入相关业务'],
  },
  ai_quote_assistant: {
    title: 'AI 报价助手',
    purpose: '根据客户需求生成可人工复核的报价建议',
    workflowStage: 'ai_quote',
    availableActions: ['输入客户需求', '生成报价建议', '复核报价'],
  },
  quote_knowledge_base: {
    title: '报价知识库',
    purpose: '查询历史项目、价格区间和报价经验',
    workflowStage: 'ai_knowledge',
    availableActions: ['搜索相似项目', '查看历史价格', '查看报价建议'],
  },
  business_narrative_report: {
    title: '智能经营报告',
    purpose: '将经营数据生成便于阅读的分析和建议',
    workflowStage: 'ai_analysis',
    availableActions: ['选择报告范围', '生成经营报告', '查看建议'],
  },
  site_photo_recognition: {
    title: '现场照片识别',
    purpose: '识别安装现场条件、障碍和安全风险',
    workflowStage: 'ai_installation',
    availableActions: ['上传现场照片', '识别现场风险', '复核识别结果'],
  },
  payment_ocr: {
    title: '收款截图识别',
    purpose: '从收款截图提取金额、时间和付款方供人工确认',
    workflowStage: 'ai_finance',
    availableActions: ['上传收款截图', '识别收款信息', '复核识别结果'],
  },
}
