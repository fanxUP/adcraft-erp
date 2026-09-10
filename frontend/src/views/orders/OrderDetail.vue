<template>
  <div class="page">
    <el-button text @click="$router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="order" v-loading="loading" ref="printOrderSection">
      <div style="display: flex; justify-content: space-between; align-items: center; margin: 16px 0">
      <h2 style="margin: 0; color: var(--ad-text)">订单 {{ order.order_no }}</h2>
      <div style="display: flex; align-items: center; gap: 8px">
      <el-button v-if="canEditItems" @click="router.push(`/orders/${order.id}/edit`)" type="primary" plain>
        编辑订单
      </el-button>
      <el-button @click="handlePrintOrder" type="primary">
        <el-icon><Printer /></el-icon> 打印预览
      </el-button>
      </div>
    </div>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="基本信息" name="info">
          <OrderProjectOverview
            :order-id="order.id"
            :status="order.status"
            :status-view="order.status_view"
            :total-amount="order.total_amount || 0"
            :paid-amount="order.paid_amount || 0"
            :cost-amount="order.cost_amount || 0"
            :gross-profit="order.gross_profit || 0"
            :design-count="designTasks.length"
            :design-completed="designCompleted"
            :production-count="productionTasks.length"
            :production-completed="productionCompleted"
            :installation-count="installationTasks.length"
            :installation-completed="installationCompleted"
            :overdue-task-count="overdueTaskCount"
            :project-progress="projectProgress"
            @select-tab="activeTab = $event"
          />
          <el-card v-if="canManageTaskScope" shadow="never" class="info-card task-scope-card">
            <template #header>
              <div class="card-header">
                <span>任务可见员工</span>
                <el-tag size="small" :type="orderTaskAssigneeIds.length ? 'warning' : 'success'">
                  {{ orderTaskAssigneeIds.length ? `已指定 ${orderTaskAssigneeIds.length} 人` : '未限制，全部可见' }}
                </el-tag>
              </div>
            </template>
            <div class="task-scope-row">
              <el-select
                v-model="orderTaskAssigneeIds"
                multiple
                filterable
                clearable
                collapse-tags
                collapse-tags-tooltip
                placeholder="不选择则全部员工可见"
                class="task-scope-select"
                :disabled="taskAssigneeSaving"
              >
                <el-option
                  v-for="employee in taskAssigneeOptions"
                  :key="employee.id"
                  :label="`${employee.name}（${employee.employee_no}）`"
                  :value="employee.id"
                />
              </el-select>
              <el-button type="primary" :loading="taskAssigneeSaving" @click="saveOrderTaskAssignees">
                保存可见范围
              </el-button>
            </div>
            <div class="task-scope-hint">
              {{ orderTaskAssigneeIds.length ? '只有选中的员工能在工作台和任务详情中看到本订单任务。' : '当前未指定员工，拥有对应任务权限的员工都能看到本订单任务。' }}
            </div>
          </el-card>
          <el-card v-if="itemProgressRows.length" shadow="never" class="info-card item-progress-card">
            <template #header>
              <div class="card-header">
                <span>订单明细进度</span>
                <span class="progress-note">每条明细独立推进，允许设计、制作、安装同时处于不同阶段</span>
              </div>
            </template>
            <el-alert
              v-if="legacyUnlinkedTaskCount > 0"
              type="warning"
              :closable="false"
              show-icon
              style="margin-bottom: 12px"
            >
              <template #title>
                <div class="legacy-alert-title">
                  <span>{{ legacyUnlinkedTaskCount }} 条历史任务还未关联订单明细</span>
                  <el-button size="small" type="warning" plain @click="activeTab = 'tasks'">查看并处理</el-button>
                </div>
              </template>
            </el-alert>
            <el-table :data="itemProgressRows" stripe border size="small">
              <el-table-column label="订单明细" min-width="180">
                <template #default="{ row }">
                  <div class="item-name">{{ row.item.item_name }}</div>
                  <div v-if="row.item.material_process" class="item-subtitle">{{ row.item.material_process }}</div>
                </template>
              </el-table-column>
              <el-table-column label="明细总进度" width="165">
                <template #default="{ row }">
                  <ProgressBar :percentage="row.overallProgress" size="sm" aria-label="明细总进度" />
                </template>
              </el-table-column>
              <el-table-column label="设计" min-width="155">
                <template #default="{ row }">
                  <ProgressBar :percentage="row.designProgress" size="sm" aria-label="设计进度" />
                  <div class="stage-line">
                    <span>{{ row.designTask ? row.item.item_name : stageLabel(row.designTask, 'design') }}</span>
                    <StatusTag v-if="row.designTask" :status="itemTaskStatusView(row.designTask, row.item.id) || itemTaskStatus(row.designTask, row.item.id)" size="sm" />
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="制作" min-width="155">
                <template #default="{ row }">
                  <ProgressBar :percentage="row.productionProgress" size="sm" aria-label="制作进度" />
                  <div class="stage-line">
                    <span>{{ row.productionTask ? row.item.item_name : stageLabel(row.productionTask, 'production') }}</span>
                    <StatusTag v-if="row.productionTask" :status="itemTaskStatusView(row.productionTask, row.item.id) || itemTaskStatus(row.productionTask, row.item.id)" size="sm" />
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="安装" min-width="155">
                <template #default="{ row }">
                  <ProgressBar :percentage="row.installationProgress" size="sm" aria-label="安装进度" />
                  <div class="stage-line">
                    <span>{{ row.installationTask ? row.item.item_name : stageLabel(row.installationTask, 'installation') }}</span>
                    <StatusTag v-if="row.installationTask" :status="itemTaskStatusView(row.installationTask, row.item.id) || itemTaskStatus(row.installationTask, row.item.id)" size="sm" />
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
          <el-card shadow="never" class="info-card">
            <el-descriptions :column="2">
              <el-descriptions-item label="订单编号">{{ order.order_no }}</el-descriptions-item>
              <el-descriptions-item label="项目名称">{{ order.project_name }}</el-descriptions-item>
             <el-descriptions-item label="状态">
                <StatusTag :status="order.status_view || order.status" size="sm" />
              </el-descriptions-item>
              <el-descriptions-item label="联系人">
                <el-input v-if="contactEditing" v-model="contactDraft.person" size="small" style="width: 140px" placeholder="联系人" />
                <template v-else>{{ order.contact_person || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="联系电话">
                <div v-if="contactEditing" style="display: flex; align-items: center; gap: 8px">
                  <el-input v-model="contactDraft.phone" size="small" style="width: 140px" placeholder="联系电话" />
                  <el-button size="small" :loading="contactSaving" @click="handleSaveContact" type="primary">保存</el-button>
                  <el-button size="small" @click="cancelContactEdit">取消</el-button>
                </div>
                <template v-else>
                  {{ order.contact_phone || '-' }}
                  <el-button v-if="order.status !== 'cancelled'" size="small" text type="primary" style="margin-left: 8px" @click="startContactEdit">编辑</el-button>
                </template>
              </el-descriptions-item>
              <el-descriptions-item label="总金额">¥ {{ order.total_amount?.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="已收金额">¥ {{ order.paid_amount?.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="未收金额">¥ {{ order.unpaid_amount?.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="安装地址">{{ order.installation_address || '-' }}</el-descriptions-item>
              <el-descriptions-item label="备注">{{ order.remark || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card shadow="never" class="info-card" style="margin-top: 16px">
            <template #header>
              <div class="card-header">
                <span>成本与利润</span>
                <div>
                  <el-button size="small" @click="handleAutoCost" :loading="autoCostLoading">自动核算</el-button>
                  <el-button size="small" @click="$router.push(`/project-costs/${order.id}`)">登记成本</el-button>
                </div>
              </div>
            </template>
            <el-descriptions :column="3">
              <el-descriptions-item label="订单金额">¥ {{ order.total_amount?.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="成本金额">¥ {{ order.cost_amount?.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="毛利">
                <el-tag :type="(order.gross_profit || 0) >= 0 ? 'success' : 'danger'" size="small">
                  ¥ {{ order.gross_profit?.toFixed(2) }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- 订单状态流程图按钮 -->
          <OrderWorkflow
            :current-status="order.status"
            :changing="changing"
            @change="handleChangeStatus"
          />
          <el-button
            v-if="order.status === 'completed'"
            plain
            style="margin-top: 12px"
            @click="handleReopenCompleted"
          >管理员撤回已完成订单</el-button>
        </el-tab-pane>

        <el-tab-pane label="订单明细" name="items">
          <el-card shadow="never" class="info-card">
            <template #header>
              <div class="card-header">
                <span>订单明细</span>
                <div style="display: flex; align-items: center; gap: 8px">
                  <el-tooltip v-if="itemEditability && !canEditItems" placement="top">
                    <template #content>
                      <div v-for="reason in itemEditability.lock_reasons" :key="reason.code">{{ reason.message }}</div>
                    </template>
                    <el-tag type="info" size="small">明细已锁定</el-tag>
                  </el-tooltip>
                </div>
              </div>
            </template>
            <el-alert
              v-if="itemEditability && canEditItems && itemEditability.requires_confirmation"
              type="warning"
              :closable="false"
              style="margin-bottom: 12px"
              title="当前订单存在关联记录，提交前会展示影响目录并要求确认；已发生事实不会被静默覆盖。"
            >
              <template #default>
                当前识别到 {{ itemEditability.association_count }} 条关联记录，明细修改后将按关联状态刷新、保留事实或生成待复核项。
              </template>
            </el-alert>
            <el-alert
              v-else-if="itemEditability && !canEditItems"
              type="info"
              :closable="false"
              style="margin-bottom: 12px"
              title="当前订单明细不可修改；请先处理阻断项或走正式变更流程。"
            >
              <template #default>
                <span v-for="(reason, index) in itemEditability.lock_reasons" :key="reason.code">
                  <span v-if="index">；</span>{{ reason.message }}
                </span>
              </template>
            </el-alert>
            <el-table :data="displayRows" stripe border size="small" :row-class-name="rowClassName">
              <el-table-column label="序号" width="55">
                <template #default="{ row, $index }">
                  <template v-if="row.type === 'item'">{{ itemIndex(row, $index) }}</template>
                </template>
              </el-table-column>
              <el-table-column label="项目内容" min-width="150">
                <template #default="{ row }">
                  <template v-if="row.type === 'group-header'">
                    <span style="font-weight: 600;">分项：{{ row.groupName }}</span>
                  </template>
                  <template v-else-if="row.type === 'group-total'">
                    <span style="font-weight: 600; float: right;">分项合计</span>
                  </template>
                  <template v-else>{{ row.item.item_name }}</template>
                </template>
              </el-table-column>
              <el-table-column label="产品/材质/工艺" min-width="150">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.material_process }}</template>
                </template>
              </el-table-column>
              <el-table-column label="规格" min-width="140">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">
                    <template v-if="row.item.specification">
                      {{ row.item.specification }}
                    </template>
                    <template v-else-if="row.item.length || row.item.width || row.item.height">
                      {{ row.item.length ?? '' }}{{ row.item.length_unit || 'm' }}
                      <template v-if="row.item.width"> x {{ row.item.width }}{{ row.item.width_unit || 'm' }}</template>
                      <template v-if="row.item.height"> x {{ row.item.height }}{{ row.item.height_unit || 'm' }}</template>
                    </template>
                    <span v-else>-</span>
                  </template>
                </template>
              </el-table-column>
              <el-table-column label="面积" width="80">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.use_area && row.item.area != null ? row.item.area.toFixed(2) : '-' }}</template>
                </template>
              </el-table-column>
              <el-table-column label="数量" width="70">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.quantity }}</template>
                </template>
              </el-table-column>
              <el-table-column label="单位" width="60">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.unit || '-' }}</template>
                </template>
              </el-table-column>
              <el-table-column label="单价" width="90">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">¥ {{ row.item.unit_price?.toFixed(2) }}</template>
                </template>
              </el-table-column>
              <el-table-column label="小计" width="110">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">¥ {{ row.item.subtotal_amount?.toFixed(2) }}</template>
                  <template v-else-if="row.type === 'group-total'"><strong>¥ {{ row.total.toFixed(2) }}</strong></template>
                </template>
              </el-table-column>
              <el-table-column label="样图" width="80">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">
                    <el-image v-if="row.item.image_url" :src="row.item.image_url" :preview-src-list="[row.item.image_url]" fit="cover" style="width: 32px; height: 32px; border-radius: 4px; cursor: pointer;" />
                    <span v-else style="color: var(--ad-text-secondary);">-</span>
                  </template>
                </template>
              </el-table-column>
              <el-table-column label="备注" min-width="120">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.remark || '-' }}</template>
                </template>
              </el-table-column>
              <el-table-column label="成本" width="110" fixed="right">
                <template #default="{ row }">
                  <el-button
                    v-if="row.type === 'item' && (row.item.lifecycle_status == null || row.item.lifecycle_status === 'active')"
                    text
                    type="primary"
                    size="small"
                    @click="openItemCost(row.item.id)"
                  >
                    登记成本
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <!-- 明细合计 -->
            <div v-if="order.items?.length" style="margin-top: 12px; padding-top: 12px; border-top: 2px solid var(--ad-primary, var(--el-color-primary)); text-align: right;">
              <div style="font-size: 16px; font-weight: 600; color: var(--ad-text); margin-bottom: 6px;">
                明细合计：¥ {{ itemsTotal.toFixed(2) }}
              </div>
              <div style="font-size: 13px; color: var(--ad-text-secondary);">
                大写金额：{{ toChineseAmount(itemsTotal) }}
              </div>
            </div>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="状态日志" name="logs">
          <el-card shadow="never" class="info-card">
            <el-timeline>
              <el-timeline-item
                v-for="log in order.status_logs"
                :key="log.id"
                :timestamp="formatDateTimeFull(log.operated_at)"
                placement="top"
              >
                <div>
                  <StatusTag v-if="log.from_status" :status="log.from_status" size="sm" />
                  <span v-else style="color: var(--ad-text-secondary)">-</span>
                  <span style="margin: 0 8px">→</span>
                  <StatusTag :status="log.to_status" size="sm" />
                  <span v-if="log.reason" style="margin-left: 8px; color: var(--ad-text-secondary)">{{ log.reason }}</span>
                </div>
              </el-timeline-item>
            </el-timeline>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="任务" name="tasks">
          <el-card v-if="legacyUnlinkedTasks.length" shadow="never" class="info-card legacy-unlinked-card" style="margin-bottom: 16px">
            <template #header>
              <div class="card-header">
                <span>待关联的历史任务</span>
                <el-tag type="warning" size="small">{{ legacyUnlinkedTasks.length }} 条</el-tag>
              </div>
            </template>
            <div class="legacy-task-note">
              这些任务仍保留原有进度和状态。进入详情后选择一个有效订单明细即可纳入对应明细的进度统计；系统不会自动拆分任务或创建下游任务。
            </div>
            <el-table :data="legacyUnlinkedTasks" stripe size="small">
              <el-table-column prop="stageLabel" label="阶段" width="90" />
              <el-table-column prop="taskNo" label="任务编号" min-width="180" />
              <el-table-column label="状态" width="140">
                <template #default="{ row }">
                  <StatusTag :status="row.status_view || row.status" size="sm" />
                </template>
              </el-table-column>
              <el-table-column label="进度" width="150">
                <template #default="{ row }">
                  <ProgressBar :percentage="row.progress" size="sm" aria-label="任务进度" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="110">
                <template #default="{ row }">
                  <el-button text type="primary" size="small" @click="openLegacyTask(row)">去关联</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never" class="info-card" style="margin-bottom: 16px">
            <template #header>
              <div class="card-header">
                <span data-ai-target="order-create-design">设计任务</span>
              </div>
            </template>
            <el-table :data="designTasks" stripe size="small" v-loading="tasksLoading">
              <el-table-column prop="design_no" label="编号" width="180" />
              <el-table-column label="订单明细" min-width="150">
                <template #default="{ row }">{{ row.item_name || '未关联订单明细' }}</template>
              </el-table-column>
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <div class="task-status-cell">
                    <StatusTag :status="row.status_view || row.status" size="sm" />
                    <el-tag v-if="row.is_overdue" type="danger" size="small">逾期</el-tag>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="进度" width="150">
                <template #default="{ row }">
                  <ProgressBar :percentage="row.progress_pct" size="sm" aria-label="设计任务进度" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button text type="primary" size="small" @click="$router.push(`/design-tasks/${row.id}`)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never" class="info-card" style="margin-bottom: 16px">
            <template #header>
              <div class="card-header">
                <span data-ai-target="order-create-production">制作任务</span>
              </div>
            </template>
            <el-table :data="productionTasks" stripe size="small" v-loading="tasksLoading">
              <el-table-column prop="production_no" label="编号" width="180" />
              <el-table-column label="订单明细" min-width="150">
                <template #default="{ row }">{{ row.item_name || '未关联订单明细' }}</template>
              </el-table-column>
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <div class="task-status-cell">
                    <StatusTag :status="row.status_view || row.status" size="sm" />
                    <el-tag v-if="row.is_overdue" type="danger" size="small">逾期</el-tag>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="进度" width="150">
                <template #default="{ row }">
                  <ProgressBar :percentage="row.progress_pct" size="sm" aria-label="制作任务进度" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button text type="primary" size="small" @click="$router.push(`/production-tasks/${row.id}`)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never" class="info-card">
            <template #header>
              <div class="card-header">
                <span data-ai-target="order-create-installation">安装任务</span>
              </div>
            </template>
            <el-table :data="installationTasks" stripe size="small" v-loading="tasksLoading">
              <el-table-column prop="installation_no" label="编号" width="180" />
              <el-table-column label="订单明细" min-width="150">
                <template #default="{ row }">{{ row.item_name || '未关联订单明细' }}</template>
              </el-table-column>
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <div class="task-status-cell">
                    <StatusTag :status="row.status_view || row.status" size="sm" />
                    <el-tag v-if="row.is_overdue" type="danger" size="small">逾期</el-tag>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="进度" width="150">
                <template #default="{ row }">
                  <ProgressBar :percentage="row.progress_pct" size="sm" aria-label="安装任务进度" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button text type="primary" size="small" @click="$router.push(`/installation-tasks/${row.id}`)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </div>

  </div>
</template>

<script setup lang="ts">
import { formatDateTimeFull } from '@/utils/datetime'
import { ref, reactive, computed, onMounted } from 'vue'
import { Printer } from '@element-plus/icons-vue'
import OrderWorkflow from './OrderWorkflow.vue'
import OrderProjectOverview from './OrderProjectOverview.vue'
import { useRoute, useRouter } from 'vue-router'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import {
  changeOrderStatus,
  getOrder,
  getOrderItemEditability,
  reopenCompletedOrder,
  autoCalculateCost,
  updateOrderContact,
  getOrderTaskAssigneeOptions,
  getOrderTaskAssignees,
  updateOrderTaskAssignees,
} from '@/api/orders'
import { getSystemSettings } from '@/api/admin'
import { getDesignTasks, getProductionTasks, getInstallationTasks } from '@/api/tasks'
import { ProgressBar, StatusTag } from '@/components/ui'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import type {
  DesignTaskResponse,
  InstallationTaskResponse,
  OrderDetailResponse,
  OrderItemEditabilityResponse,
  OrderItemResponse,
  ProductionTaskResponse,
  StatusView,
  TaskAssigneeOption,
} from '@/types/api'

const route = useRoute()
const router = useRouter()
const aiStore = useAiAssistantStore()
const authStore = useAuthStore()
const loading = ref(false)
const changing = ref(false)
const tasksLoading = ref(false)
const order = ref<OrderDetailResponse | null>(null)
const activeTab = ref('info')
// 状态管理由 OrderWorkflow 组件接管

const designTasks = ref<DesignTaskResponse[]>([])
const productionTasks = ref<ProductionTaskResponse[]>([])
const installationTasks = ref<InstallationTaskResponse[]>([])
const autoCostLoading = ref(false)
const contactEditing = ref(false)
const contactSaving = ref(false)
const contactDraft = reactive({ person: '', phone: '' })
const itemEditability = ref<OrderItemEditabilityResponse | null>(null)
const canEditItems = computed(() => itemEditability.value?.can_edit_items === true)
const canManageTaskScope = computed(() => authStore.hasPermission('order:task_assign'))
const taskAssigneeOptions = ref<TaskAssigneeOption[]>([])
const orderTaskAssigneeIds = ref<string[]>([])
const taskAssigneeSaving = ref(false)

type OrderProgressTask = DesignTaskResponse | ProductionTaskResponse | InstallationTaskResponse
type LegacyUnlinkedTaskRow = {
  stageLabel: string
  taskNo: string
  status: string
  status_view?: StatusView | null
  progress: number
  route: string
}
type ItemProgressRow = {
  item: OrderItemResponse
  designTask: DesignTaskResponse | null
  productionTask: ProductionTaskResponse | null
  installationTask: InstallationTaskResponse | null
  designProgress: number
  productionProgress: number
  installationProgress: number
  overallProgress: number
}

function startContactEdit() {
  contactDraft.person = order.value?.contact_person || ''
  contactDraft.phone = order.value?.contact_phone || ''
  contactEditing.value = true
}
function cancelContactEdit() {
  contactEditing.value = false
}
async function handleSaveContact() {
  contactSaving.value = true
  try {
    order.value = await updateOrderContact(route.params.id as string, {
      contact_person: contactDraft.person || null,
      contact_phone: contactDraft.phone || null,
    })
    contactEditing.value = false
    ElMessage.success('联系人已更新')
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally { contactSaving.value = false }
}

const itemsTotal = computed(() => (order.value?.items || []).reduce((s, i) => s + (i.subtotal_amount || 0), 0))

async function fetchItemEditability() {
  try {
    itemEditability.value = await getOrderItemEditability(route.params.id as string)
  } catch {
    itemEditability.value = null
  }
}

const designCompleted = computed(() => designTasks.value.filter(task => ['confirmed', 'completed'].includes(task.status)).length)
const productionCompleted = computed(() => productionTasks.value.filter(task => task.status === 'completed').length)
const installationCompleted = computed(() => installationTasks.value.filter(task => task.status === 'completed').length)
const overdueTaskCount = computed(() => [...designTasks.value, ...productionTasks.value, ...installationTasks.value]
  .filter(task => task.is_overdue).length)

function findItemTask<T extends OrderProgressTask>(tasks: T[], itemId: string): T | null {
  return tasks.find(task => (
    (task.order_item_ids?.includes(itemId) || task.order_item_id === itemId)
    && task.status !== 'cancelled'
  )) || null
}

function taskIsUnlinked(task: OrderProgressTask) {
  return task.status !== 'cancelled'
    && !(task.order_item_ids?.length || task.order_item_id)
}

const itemProgressRows = computed<ItemProgressRow[]>(() => {
  return (order.value?.items || []).map(item => {
    const designTask = findItemTask(designTasks.value, item.id)
    const productionTask = findItemTask(productionTasks.value, item.id)
    const installationTask = findItemTask(installationTasks.value, item.id)
    const designProgress = itemTaskProgress(designTask, item.id)
    const productionProgress = itemTaskProgress(productionTask, item.id)
    const installationProgress = itemTaskProgress(installationTask, item.id)
    return {
      item,
      designTask,
      productionTask,
      installationTask,
      designProgress,
      productionProgress,
      installationProgress,
      overallProgress: Math.round((designProgress + productionProgress + installationProgress) / 3),
    }
  })
})

const legacyUnlinkedTaskCount = computed(() => [...designTasks.value, ...productionTasks.value, ...installationTasks.value]
  .filter(taskIsUnlinked).length)

const legacyUnlinkedTasks = computed<LegacyUnlinkedTaskRow[]>(() => [
  ...designTasks.value
    .filter(taskIsUnlinked)
    .map(task => ({
      stageLabel: '设计',
      taskNo: task.design_no,
      status: task.status,
      status_view: task.status_view,
      progress: progressPct(task.progress_pct),
      route: `/design-tasks/${task.id}`,
    })),
  ...productionTasks.value
    .filter(taskIsUnlinked)
    .map(task => ({
      stageLabel: '制作',
      taskNo: task.production_no,
      status: task.status,
      status_view: task.status_view,
      progress: progressPct(task.progress_pct),
      route: `/production-tasks/${task.id}`,
    })),
  ...installationTasks.value
    .filter(taskIsUnlinked)
    .map(task => ({
      stageLabel: '安装',
      taskNo: task.installation_no,
      status: task.status,
      status_view: task.status_view,
      progress: progressPct(task.progress_pct),
      route: `/installation-tasks/${task.id}`,
    })),
])

const projectProgress = computed(() => {
  if (itemProgressRows.value.length) {
    return Math.round(itemProgressRows.value.reduce((sum, row) => sum + row.overallProgress, 0) / itemProgressRows.value.length)
  }
  const tasks = [...designTasks.value, ...productionTasks.value, ...installationTasks.value]
    .filter(task => task.status !== 'cancelled')
  if (!tasks.length) return 0
  return Math.round(tasks.reduce((sum, task) => sum + progressPct(task.progress_pct), 0) / tasks.length)
})

function progressPct(value: number | undefined) {
  return Math.min(100, Math.max(0, Number(value ?? 0)))
}

function itemTaskStatus(task: OrderProgressTask | null, itemId: string) {
  if (!task) return ''
  return task.order_item_states?.[itemId]?.status || task.status
}

function itemTaskStatusView(task: OrderProgressTask | null, itemId: string) {
  return task?.order_item_states?.[itemId]?.status_view || task?.status_view || null
}

function itemTaskProgress(task: OrderProgressTask | null, itemId: string) {
  if (!task) return 0
  return progressPct(task.order_item_states?.[itemId]?.progress_pct ?? task.progress_pct)
}

function openLegacyTask(task: LegacyUnlinkedTaskRow) {
  router.push(task.route)
}

function openItemCost(itemId: string) {
  router.push({
    path: `/project-costs/${route.params.id as string}`,
    query: { order_item_id: itemId },
  })
}

function stageLabel(task: OrderProgressTask | null, stage: 'design' | 'production' | 'installation') {
  if (task) return '已关联任务'
  return stage === 'design' ? '未生成设计任务' : '未进入此阶段'
}

function toChineseAmount(n: number): string {
  const digits = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
  const units = ['', '拾', '佰', '仟']
  const bigUnits = ['', '万', '亿']

  if (n === 0) return '零元整'
  const negative = n < 0
  n = Math.abs(n)

  const intPart = Math.floor(n)
  const decPart = Math.round((n - intPart) * 100)
  const jiao = Math.floor(decPart / 10)
  const fen = decPart % 10

  let result = ''

  if (intPart > 0) {
    const str = String(intPart)
    const len = str.length
    let zeroFlag = false
    for (let i = 0; i < len; i++) {
      const d = parseInt(str[i])
      const pos = len - 1 - i
      const unitIdx = pos % 4
      const bigIdx = Math.floor(pos / 4)

      if (d === 0) {
        zeroFlag = true
        if (unitIdx === 0 && bigUnits[bigIdx]) {
          result += bigUnits[bigIdx]
          zeroFlag = false
        }
      } else {
        if (zeroFlag) { result += '零'; zeroFlag = false }
        result += digits[d] + units[unitIdx]
        if (unitIdx === 0 && bigUnits[bigIdx]) result += bigUnits[bigIdx]
      }
    }
    result += '元'
  }

  if (jiao === 0 && fen === 0) {
    result += '整'
  } else {
    if (jiao > 0) result += digits[jiao] + '角'
    else if (intPart > 0) result += '零'
    if (fen > 0) result += digits[fen] + '分'
  }

  return (negative ? '负' : '') + result
}

type DisplayRow =
  | { type: 'group-header'; groupName: string }
  | { type: 'item'; item: OrderItemResponse; groupName: string }
  | { type: 'group-total'; groupName: string; total: number }

const displayRows = computed<DisplayRow[]>(() => {
  const items = order.value?.items || []
  const grouped = new Map<string, OrderItemResponse[]>()
  const ungrouped: OrderItemResponse[] = []

  for (const item of items) {
    if (item.group_name) {
      if (!grouped.has(item.group_name)) grouped.set(item.group_name, [])
      grouped.get(item.group_name)!.push(item)
    } else {
      ungrouped.push(item)
    }
  }

  const rows: DisplayRow[] = []
  for (const [groupName, groupItems] of grouped) {
    rows.push({ type: 'group-header', groupName })
    for (const item of groupItems) rows.push({ type: 'item', item, groupName })
    const total = groupItems.reduce((s, i) => s + (i.subtotal_amount || 0), 0)
    rows.push({ type: 'group-total', groupName, total })
  }
  for (const item of ungrouped) rows.push({ type: 'item', item, groupName: '' })
  return rows
})

function rowClassName({ row }: { row: DisplayRow }) {
  if (row.type === 'group-header') return 'group-header-row'
  if (row.type === 'group-total') return 'group-total-row'
  return ''
}

function itemIndex(row: DisplayRow, displayIdx: number): number {
  let count = 0
  for (let i = 0; i <= displayIdx; i++) {
    if (displayRows.value[i].type === 'item') count++
  }
  return count
}

async function fetchOrder() {
  loading.value = true
  try {
    order.value = await getOrder(route.params.id as string)
    if (order.value) {
      await fetchItemEditability()
      aiStore.setPageContext({
        order_id: order.value.id,
        order_no: order.value.order_no,
        customer_id: order.value.customer_id,
        customer_name: order.value.customer_name || '',
        project_name: order.value.project_name,
        business_status: order.value.status,
      })
    }
  } finally { loading.value = false }
}

async function loadOrderTaskAssignees() {
  if (!canManageTaskScope.value) return
  try {
    const [options, current] = await Promise.all([
      getOrderTaskAssigneeOptions(),
      getOrderTaskAssignees(route.params.id as string),
    ])
    taskAssigneeOptions.value = options
    orderTaskAssigneeIds.value = current.employee_ids
  } catch {
    taskAssigneeOptions.value = []
    orderTaskAssigneeIds.value = []
  }
}

async function saveOrderTaskAssignees() {
  if (!order.value || !canManageTaskScope.value) return
  taskAssigneeSaving.value = true
  try {
    const result = await updateOrderTaskAssignees(order.value.id, orderTaskAssigneeIds.value)
    orderTaskAssigneeIds.value = result.employee_ids
    ElMessage.success(result.is_restricted ? '任务可见员工已保存' : '已清除限制，全部员工可见')
  } finally {
    taskAssigneeSaving.value = false
  }
}

async function fetchTasks() {
  if (!authStore.hasPermission('design_task:list')
    && !authStore.hasPermission('production_task:list')
    && !authStore.hasPermission('installation_task:list')) {
    designTasks.value = []
    productionTasks.value = []
    installationTasks.value = []
    return
  }
  tasksLoading.value = true
  try {
    const orderId = route.params.id as string
    const [d, p, i] = await Promise.all([
      authStore.hasPermission('design_task:list')
        ? getDesignTasks({ order_id: orderId, page_size: 100 })
        : Promise.resolve(null),
      authStore.hasPermission('production_task:list')
        ? getProductionTasks({ order_id: orderId, page_size: 100 })
        : Promise.resolve(null),
      authStore.hasPermission('installation_task:list')
        ? getInstallationTasks({ order_id: orderId, page_size: 100 })
        : Promise.resolve(null),
    ])
    designTasks.value = d?.items || []
    productionTasks.value = p?.items || []
    installationTasks.value = i?.items || []
  } finally { tasksLoading.value = false }
}

async function handleChangeStatus(to_status: string) {
  const labels: Record<string, string> = {
    pending_confirm: '待确认', confirmed: '已确认', designing: '设计中',
    in_production: '生产中', in_installation: '安装中',
    completed: '已完成', cancelled: '已取消',
  }
  const label = labels[to_status] || to_status
  const msg = to_status === 'cancelled'
    ? '确定取消此订单？订单将移入回收站，后续可在回收站中恢复。'
    : `确定将订单状态变更为「${label}」？`
  await ElMessageBox.confirm(msg, '变更状态', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
  })
  changing.value = true
  try {
    order.value = await changeOrderStatus(route.params.id as string, {
      to_status,
      reason: undefined,
    })
    ElMessage.success(`状态已变更为「${label}」`)
    // 取消会软删订单进回收站，导航刷新查不到已删订单，跳过
    if (to_status !== 'cancelled') await aiStore.notifyBusinessMutation()
    // 取消订单后自动跳转回订单管理页
    if (to_status === 'cancelled') router.push('/orders')
  } finally { changing.value = false }
}

async function handleReopenCompleted() {
  if (!order.value) return
  const { value: reason } = await ElMessageBox.prompt(
    '撤回后订单将回到“安装中”，之后可继续取消。请输入撤回原因。',
    '撤回已完成订单',
    {
      confirmButtonText: '确认撤回',
      cancelButtonText: '取消',
      inputPlaceholder: '例如：客户要求终止项目',
      inputValidator: (value) => value.trim() ? true : '请输入撤回原因',
    },
  )
  changing.value = true
  try {
    order.value = await reopenCompletedOrder(order.value.id, reason)
    ElMessage.success('订单已撤回到安装中状态，现在可以取消订单')
  } finally { changing.value = false }
}

async function handleAutoCost() {
  await ElMessageBox.confirm('将覆盖现有成本数据，确定继续？', '自动核算', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
  autoCostLoading.value = true
  try {
    order.value = await autoCalculateCost(route.params.id as string)
    ElMessage.success('自动核算完成')
  } finally { autoCostLoading.value = false }
}

const printOrderSection = ref(null)

async function handlePrintOrder() {
  // Build print-friendly HTML from order data
  const o = order.value
  if (!o) return
  let companyName = ''
  let companyPhone = ''
  try {
    const s = await getSystemSettings()
    companyName = s.COMPANY_NAME || ''
    companyPhone = s.COMPANY_PHONE || ''
  } catch { /* 取不到设置时使用占位 */ }
  const wrapper = document.createElement('div')
  wrapper.id = '__print_a4_wrapper__'
  wrapper.className = 'print-a4-wrapper'

  let html = '<div class="print-company" style="text-align:center;margin-bottom:8px;">'
  html += '<div style="font-size:20px;font-weight:700;">' + (companyName || '广告制作公司') + '</div>'
  html += '<div style="font-size:13px;color:#666;">联系电话: ' + (companyPhone || '__________') + '</div>'
  html += '</div>'
  html += '<div class="print-title">订单 ' + o.order_no + '</div>'
  html += '<div class="print-info">'
  html += '<div class="print-info-row"><span><strong>订单编号:</strong> ' + (o.order_no || '-') + '</span><span><strong>项目名称:</strong> ' + (o.project_name || '-') + '</span></div>'
  html += '<div class="print-info-row"><span><strong>联系人:</strong> ' + (o.contact_person || '-') + '</span><span><strong>联系电话:</strong> ' + (o.contact_phone || '-') + '</span></div>'
  html += '<div class="print-info-row"><span><strong>安装地址:</strong> ' + (o.installation_address || '-') + '</span><span><strong>总金额:</strong> ¥' + (o.total_amount || 0).toFixed(2) + '</span></div>'
  html += '<div class="print-info-row"><span><strong>已收金额:</strong> ¥' + (o.paid_amount || 0).toFixed(2) + '</span><span><strong>未收金额:</strong> ¥' + (o.unpaid_amount || 0).toFixed(2) + '</span></div>'
  if (o.remark) html += '<div class="print-info-row"><span><strong>备注:</strong> ' + o.remark + '</span></div>'
  html += '</div>'
  
  // Items table
  html += '<table class="print-table"><thead><tr><th class="center">序号</th><th>项目内容</th><th>产品/材质/工艺</th><th>规格</th><th class="numeric">数量</th><th class="center">单位</th><th class="numeric">单价</th><th class="numeric">小计</th><th>备注</th></tr></thead><tbody>'
  const items = o.items || []
  if (items.length === 0) {
    html += '<tr><td colspan="9" class="print-empty">暂无明细</td></tr>'
  } else {
    items.forEach((item, i) => {
      html += '<tr>'
      html += '<td class="center">' + (i + 1) + '</td>'
      html += '<td>' + (item.item_name || '') + '</td>'
      html += '<td>' + (item.material_process) + '</td>'
      html += '<td>' + (item.specification || '-') + '</td>'
      html += '<td class="numeric">' + (item.quantity != null ? item.quantity : '') + '</td>'
      html += '<td class="center">' + (item.unit || '-') + '</td>'
      html += '<td class="numeric">' + (item.unit_price != null ? item.unit_price.toFixed(2) : '-') + '</td>'
      html += '<td class="numeric">' + (item.subtotal_amount != null ? item.subtotal_amount.toFixed(2) : '-') + '</td>'
      html += '<td>' + (item.remark || '') + '</td>'
      html += '</tr>'
    })
  }
  html += '</tbody></table>'
  
  // Summary
  html += '<div class="print-summary">'
  html += '<div class="print-summary-row"><span><strong>合计金额:</strong> ¥' + (o.total_amount || 0).toFixed(2) + '</span></div>'
  html += '</div>'
  
  wrapper.innerHTML = html
  document.body.appendChild(wrapper)
  window.print()
  setTimeout(() => { const el = document.getElementById('__print_a4_wrapper__'); if (el) el.remove() }, 300)
}

onMounted(() => { fetchOrder(); fetchTasks(); loadOrderTaskAssignees() })
</script>

<style scoped>
.page { padding: 0; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.task-scope-card { margin-top: 16px; }
.task-scope-row { display: flex; align-items: center; gap: 12px; }
.task-scope-select { flex: 1; min-width: 260px; }
.task-scope-hint { margin-top: 8px; color: var(--ad-text-secondary); font-size: 12px; line-height: 1.6; }
.item-progress-card { margin-top: 16px; }
.item-progress-card .progress-note { color: var(--ad-text-secondary); font-size: 12px; font-weight: normal; }
.legacy-alert-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.legacy-unlinked-card .legacy-task-note { margin-bottom: 12px; color: var(--ad-text-secondary); font-size: 12px; line-height: 1.6; }
.item-name { color: var(--ad-text); font-weight: 600; }
.item-subtitle { margin-top: 3px; color: var(--ad-text-secondary); font-size: 12px; }
.stage-line { display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-top: 3px; color: var(--ad-text-secondary); font-size: 12px; }
.stage-line span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-status-cell { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.item-form :deep(.el-form-item) { margin-bottom: 14px; }
.impact-section-title { font-weight: 600; color: var(--ad-text); margin: 12px 0 8px; }
.amount-up { color: var(--el-color-success); }
.amount-down { color: var(--el-color-danger); }
:deep(.group-header-row) { background: var(--ad-bg-secondary, #f5f7fa) !important; }
:deep(.group-header-row td) { border-bottom: 2px solid var(--ad-primary, #409eff) !important; }
:deep(.group-total-row) { background: var(--ad-bg-secondary, #fafafa) !important; }
:deep(.group-total-row td) { border-top: 1px solid var(--ad-border, #dcdfe6) !important; font-weight: 600; }
</style>
