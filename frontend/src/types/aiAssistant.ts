// AI Assistant TypeScript types — mirrors backend Pydantic schemas

export interface AiPageContext {
  page?: string
  business_type?: string
  business_id?: string
  customer_id?: string
  customer_name?: string
  customer_no?: string
  order_id?: string
  order_no?: string
  quote_id?: string
  quote_no?: string
  project_name?: string
  task_id?: string
  task_type?: string
}

export interface AiMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'tool' | 'system'
  content: string | null
  metadata_json?: Record<string, unknown> | null
  created_at?: string | null
}

export interface AiSession {
  id: string
  title: string | null
  current_page: string | null
  current_business_type: string | null
  current_business_id: string | null
  created_at: string | null
  updated_at: string | null
}

export interface AiToolCallResult {
  status: string
  result?: Record<string, unknown> | null
  error_message?: string | null
  tool_name?: string
  is_preview?: boolean
}

export interface AiPendingAction {
  id: string
  tool_name: string
  preview_data: Record<string, unknown>
}

export interface AiChatResponse {
  session_id: string
  message_id: string
  reply: string
  tool_calls: AiToolCallResult[]
  pending_action: AiPendingAction | null
}

// Suggested prompts by page
export const PAGE_SUGGESTED_PROMPTS: Record<string, string[]> = {
  dashboard: ['查看今日任务', '查看所有客户', '有哪些待处理订单'],
  customer_list: ['搜索客户', '查看欠款客户'],
  customer_detail: ['这个客户欠多少钱', '这个客户有哪些订单'],
  order_list: ['搜索订单', '查看未完成订单'],
  order_detail: ['这个订单做到哪了', '查看这个订单的收款情况'],
  quote_list: ['帮我生成报价草稿'],
  cdr_quote_list: ['帮我生成智能报价'],
  cdr_quote_detail: ['这个报价是什么内容', '生成这个报价的订单'],
  design_task_list: ['今天有哪些设计任务'],
  design_task_detail: ['这个设计任务什么状态'],
  production_task_list: ['今天有哪些制作任务'],
  production_task_detail: ['这个制作任务什么状态'],
  installation_task_list: ['今天有哪些安装任务', '安排明天安装'],
  installation_task_detail: ['这个安装任务什么状态'],
  vehicle_dashboard: ['今天有哪些用车申请'],
  vehicle_list: ['搜索车辆'],
  aerial_dashboard: ['今天高空车出车情况'],
  receivables: ['有哪些欠款客户'],
  '': ['你好', '有什么可以帮我的'],
}

// Quick action buttons
export const PAGE_QUICK_ACTIONS: Record<string, { label: string; prompt: string }[]> = {
  dashboard: [
    { label: '📋 今日任务', prompt: '查询今日的设计、制作和安装任务' },
    { label: '👥 客户列表', prompt: '列出所有客户' },
    { label: '📦 待处理订单', prompt: '查看有哪些未完成的订单' },
  ],
  customer_list: [
    { label: '🔍 搜索', prompt: '搜索客户' },
    { label: '💰 欠款客户', prompt: '查看客户的欠款情况' },
  ],
  customer_detail: [
    { label: '💰 欠款', prompt: '这个客户欠多少钱' },
    { label: '📋 订单', prompt: '这个客户有哪些订单' },
  ],
  order_detail: [
    { label: '📊 进度', prompt: '这个订单做到哪了' },
    { label: '💰 收款', prompt: '这个订单的收款情况' },
    { label: '📋 任务', prompt: '这个订单有哪些任务' },
  ],
  cdr_quote_detail: [
    { label: '📋 内容', prompt: '这个报价是什么内容' },
    { label: '📦 转订单', prompt: '把这个报价转为订单' },
  ],
  installation_task_list: [
    { label: '🔍 今日安装', prompt: '查询今天的安装任务' },
    { label: '📅 安排安装', prompt: '帮我安排明天安装' },
  ],
  design_task_list: [
    { label: '🔍 今日设计', prompt: '查询今天的设计任务' },
  ],
  production_task_list: [
    { label: '🔍 今日制作', prompt: '查询今天的制作任务' },
  ],
}
