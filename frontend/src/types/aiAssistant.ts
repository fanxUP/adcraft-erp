// AI Assistant TypeScript types — mirrors backend Pydantic schemas

export interface AiPageContext {
  page?: string
  page_title?: string
  page_purpose?: string
  workflow_stage?: string
  available_actions?: string[]
  business_type?: string
  business_id?: string
  business_status?: string
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

export interface AiWorkflowAction {
  label: string
  target_page: string
  target_path: string
  target_status?: string
  target_key?: string
}

export type AiWorkflowStepState = 'completed' | 'current' | 'pending' | 'blocked'

export interface AiWorkflowProgressStep {
  key: string
  label: string
  state: AiWorkflowStepState
  detail: string
}

export interface AiWorkflowProgress {
  completed_steps: number
  total_steps: number
  percent: number
  current_stage_key: string
  steps: AiWorkflowProgressStep[]
}

export interface AiWorkflowAlert {
  code: string
  severity: 'info' | 'warning' | 'danger'
  title: string
  detail: string
}

export interface AiWorkflowGuidance {
  business_type: string
  business_id: string
  current_status: string
  current_step: string
  blockers: string[]
  next_action: AiWorkflowAction | null
  completion_signal: string
  allowed_next_statuses: string[]
  progress?: AiWorkflowProgress
  alerts: AiWorkflowAlert[]
}

export interface AiPageActionGuide {
  label: string
  target_path: string
  target_key: string
  target_status?: string
}

export type AiPageGuideState =
  | 'idle'
  | 'restored'
  | 'locating'
  | 'active'
  | 'completed'
  | 'not_found'

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
