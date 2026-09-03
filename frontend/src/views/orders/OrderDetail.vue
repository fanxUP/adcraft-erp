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
            @select-tab="activeTab = $event"
          />
          <el-card shadow="never" class="info-card">
            <el-descriptions :column="2">
              <el-descriptions-item label="订单编号">{{ order.order_no }}</el-descriptions-item>
              <el-descriptions-item label="项目名称">{{ order.project_name }}</el-descriptions-item>
             <el-descriptions-item label="状态">
                <el-tag :type="statusColor(order.status)">{{ statusLabel(order.status) }}</el-tag>
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
              <el-table-column v-if="canEditItems" label="操作" width="130" fixed="right">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">
                    <el-button text type="primary" size="small" @click="openEditItem(row.item)">编辑</el-button>
                    <el-button text type="danger" size="small" @click="handleDeleteItem(row.item)">删除</el-button>
                  </template>
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

        <el-dialog v-model="itemDialogVisible" title="编辑订单明细" width="760px" destroy-on-close>
          <el-form label-width="100px" class="item-form">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="项目内容" required>
                  <el-input v-model="itemForm.item_name" maxlength="255" placeholder="请输入项目内容" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="材质/工艺">
                  <el-input v-model="itemForm.material_process" placeholder="例如：写真/铝板" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="数量" required>
                  <el-input-number v-model="itemForm.quantity" :min="0.001" :precision="3" controls-position="right" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="单位">
                  <el-input v-model="itemForm.unit" placeholder="套/个/张" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="计价模式">
                  <el-select v-model="itemForm.use_area" style="width: 100%">
                    <el-option :value="false" label="按数量" />
                    <el-option :value="true" label="按面积" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="宽度">
                  <el-input-number v-model="itemForm.width" :min="0" :precision="3" controls-position="right" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="高度">
                  <el-input-number v-model="itemForm.height" :min="0" :precision="3" controls-position="right" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="件数">
                  <el-input-number v-model="itemForm.pieces" :min="0.01" :precision="2" controls-position="right" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="单价" required>
                  <el-input-number v-model="itemForm.unit_price" :min="0" :precision="2" controls-position="right" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="其他费用">
                  <el-input-number v-model="itemForm.other_fee" :min="0" :precision="2" controls-position="right" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="分组">
                  <el-input v-model="itemForm.group_name" placeholder="可选" />
                </el-form-item>
              </el-col>
              <el-col :span="24">
                <el-form-item label="变更原因" required>
                  <el-input v-model="itemReason" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="请说明修改原因" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
          <el-alert v-if="itemPreview" :type="itemPreview.can_apply ? 'success' : 'warning'" :closable="false" style="margin-top: 8px">
            <template #default>
              变更前 ¥{{ itemPreview.before.total_amount.toFixed(2) }}，变更后 ¥{{ itemPreview.after.total_amount.toFixed(2) }}，差额
              <span :class="itemPreview.delta >= 0 ? 'amount-up' : 'amount-down'">¥{{ itemPreview.delta.toFixed(2) }}</span>；
              未收金额将变为 ¥{{ itemPreview.after.unpaid_amount.toFixed(2) }}。
              <span v-if="!itemPreview.can_apply">
                <span v-for="(reason, index) in itemPreview.lock_reasons" :key="reason.code">
                  <span v-if="index">；</span>{{ reason.message }}
                </span>
              </span>
            </template>
          </el-alert>
          <template #footer>
            <el-button @click="itemDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="itemSaving" @click="handleSaveItem">预检并保存</el-button>
          </template>
        </el-dialog>

        <el-dialog
          v-model="impactDialogVisible"
          title="确认修改并刷新关联数据"
          width="980px"
          :close-on-click-modal="false"
          destroy-on-close
        >
          <template v-if="itemPreview">
            <el-alert
              :type="itemPreview.requires_high_risk_ack ? 'warning' : 'info'"
              :closable="false"
              style="margin-bottom: 14px"
            >
              <template #title>
                {{ mutationDecisionLabel(itemPreview.decision) }}
              </template>
              <div>
                本次{{ mutationOperationLabel(itemPreview.operation) }}会生成变更批次并刷新可安全刷新的关联项；已收款、已出库、已验收、已结算和已签署合同等事实只保留并核对差额。
              </div>
            </el-alert>

            <el-descriptions :column="3" border size="small" style="margin-bottom: 14px">
              <el-descriptions-item label="订单总额">
                ¥{{ itemPreview.before.total_amount.toFixed(2) }} → ¥{{ itemPreview.after.total_amount.toFixed(2) }}
              </el-descriptions-item>
              <el-descriptions-item label="已收金额">¥{{ itemPreview.after.paid_amount.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="未收金额">¥{{ itemPreview.after.unpaid_amount.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="成本">¥{{ itemPreview.after.cost_amount.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="毛利">¥{{ itemPreview.after.gross_profit.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="金额差额">
                <span :class="itemPreview.delta >= 0 ? 'amount-up' : 'amount-down'">¥{{ itemPreview.delta.toFixed(2) }}</span>
              </el-descriptions-item>
            </el-descriptions>

            <div class="impact-section-title">关联目录（{{ itemPreview.association_catalog.length }} 条）</div>
            <el-table
              v-if="itemPreview.association_catalog.length"
              :data="itemPreview.association_catalog"
              border
              stripe
              size="small"
              max-height="360"
            >
              <el-table-column prop="label" label="关联模块" width="125" />
              <el-table-column label="记录编号" min-width="145">
                <template #default="{ row }">{{ row.record_no || row.record_id }}</template>
              </el-table-column>
              <el-table-column label="关联方式" width="95">
                <template #default="{ row }">{{ relationTypeLabel(row.relation_type) }}</template>
              </el-table-column>
              <el-table-column label="状态" width="105">
                <template #default="{ row }">{{ relationStatusLabel(row.status) }}</template>
              </el-table-column>
              <el-table-column label="处理动作" min-width="190">
                <template #default="{ row }">{{ relationActionLabel(row.action) }}</template>
              </el-table-column>
              <el-table-column label="风险" width="70">
                <template #default="{ row }">
                  <el-tag :type="riskTagType(row.risk)" size="small">{{ riskLabel(row.risk) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="说明" min-width="250">
                <template #default="{ row }">{{ row.note || '-' }}</template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="本次没有可识别的关联记录" :image-size="60" />

            <el-checkbox v-if="itemPreview.requires_high_risk_ack" v-model="highRiskAcknowledged" style="margin-top: 14px">
              我已阅读上述高风险关联项，确认提交本次修改，并接受系统生成的差异/待复核项。
            </el-checkbox>
          </template>
          <template #footer>
            <el-button @click="cancelImpactConfirmation">返回修改</el-button>
            <el-button
              type="primary"
              :loading="itemSaving"
              :disabled="Boolean(itemPreview?.requires_high_risk_ack && !highRiskAcknowledged)"
              @click="confirmImpactAndApply"
            >
              确认修改并刷新关联数据
            </el-button>
          </template>
        </el-dialog>
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
                  <el-tag v-if="log.from_status" size="small">{{ statusLabel(log.from_status) }}</el-tag>
                  <span v-else style="color: var(--ad-text-secondary)">-</span>
                  <span style="margin: 0 8px">→</span>
                  <el-tag :type="statusColor(log.to_status)" size="small">{{ statusLabel(log.to_status) }}</el-tag>
                  <span v-if="log.reason" style="margin-left: 8px; color: var(--ad-text-secondary)">{{ log.reason }}</span>
                </div>
              </el-timeline-item>
            </el-timeline>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="任务" name="tasks">
          <el-card shadow="never" class="info-card" style="margin-bottom: 16px">
            <template #header>
              <div class="card-header">
                <span data-ai-target="order-create-design">设计任务</span>
              </div>
            </template>
            <el-table :data="designTasks" stripe size="small" v-loading="tasksLoading">
              <el-table-column prop="design_no" label="编号" width="180" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="designStatusColor(row.status)" size="small">{{ designStatusLabel(row.status) }}</el-tag>
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
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="prodStatusColor(row.status)" size="small">{{ prodStatusLabel(row.status) }}</el-tag>
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
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="instStatusColor(row.status)" size="small">{{ instStatusLabel(row.status) }}</el-tag>
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
  deleteOrderItem,
  getOrder,
  getOrderItemEditability,
  previewOrderItemMutation,
  reopenCompletedOrder,
  autoCalculateCost,
  updateOrderContact,
  updateOrderItem,
} from '@/api/orders'
import { getSystemSettings } from '@/api/admin'
import { getDesignTasks, getProductionTasks, getInstallationTasks } from '@/api/tasks'
import { ElMessage, ElMessageBox } from 'element-plus'
import type {
  DesignTaskResponse,
  InstallationTaskResponse,
  OrderDetailResponse,
  OrderItemMutationFields,
  OrderItemEditabilityResponse,
  OrderItemMutationImpactResponse,
  OrderItemResponse,
  ProductionTaskResponse,
} from '@/types/api'

const route = useRoute()
const router = useRouter()
const aiStore = useAiAssistantStore()
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
const itemDialogVisible = ref(false)
const itemSaving = ref(false)
const editingItemId = ref<string | null>(null)
const itemReason = ref('')
const itemPreview = ref<OrderItemMutationImpactResponse | null>(null)
const impactDialogVisible = ref(false)
const highRiskAcknowledged = ref(false)

type PendingItemMutation = {
  operation: 'update' | 'delete'
  itemId?: string
  data?: OrderItemMutationFields
  reason: string
}

const pendingMutation = ref<PendingItemMutation | null>(null)

const emptyItemForm = (): OrderItemMutationFields => ({
  item_name: '',
  material_process: '',
  quantity: 1,
  unit: '',
  use_area: false,
  quantity_mode: 'piece',
  pieces: 1,
  length: undefined,
  length_unit: 'm',
  width: undefined,
  width_unit: 'm',
  height: undefined,
  height_unit: 'm',
  unit_price: 0,
  process_fee: 0,
  installation_fee: 0,
  design_fee: 0,
  transport_fee: 0,
  other_fee: 0,
  remark: '',
  image_url: '',
  group_name: '',
  group_id: null,
})
const itemForm = reactive<OrderItemMutationFields>(emptyItemForm())
const canEditItems = computed(() => itemEditability.value?.can_edit_items === true)

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

function openEditItem(item: OrderItemResponse) {
  editingItemId.value = item.id
  Object.assign(itemForm, emptyItemForm(), {
    item_name: item.item_name,
    product_id: item.product_id,
    material_id: item.material_id,
    process_id: item.process_id,
    length: item.length,
    length_unit: item.length_unit || 'm',
    width: item.width,
    width_unit: item.width_unit || 'm',
    height: item.height,
    height_unit: item.height_unit || 'm',
    quantity: item.quantity,
    unit: item.unit || '',
    use_area: item.use_area,
    quantity_mode: item.quantity_mode || 'piece',
    pieces: item.pieces,
    unit_price: item.unit_price,
    process_fee: item.process_fee || 0,
    installation_fee: item.installation_fee || 0,
    design_fee: item.design_fee || 0,
    transport_fee: item.transport_fee || 0,
    other_fee: item.other_fee || 0,
    remark: item.remark || '',
    image_url: item.image_url || '',
    sort_order: item.sort_order,
    group_name: item.group_name || '',
    group_id: item.group_id || null,
    material_process: item.material_process || '',
  })
  itemReason.value = ''
  itemPreview.value = null
  itemDialogVisible.value = true
}

function itemMutationPayload(): OrderItemMutationFields {
  const payload: OrderItemMutationFields = {}
  for (const [key, value] of Object.entries(itemForm)) {
    ;(payload as Record<string, unknown>)[key] = value === undefined ? null : value
  }
  return payload
}

async function fetchItemEditability() {
  try {
    itemEditability.value = await getOrderItemEditability(route.params.id as string)
  } catch {
    itemEditability.value = null
  }
}

async function previewCurrentItem() {
  if (!order.value?.updated_at) {
    ElMessage.error('订单版本信息缺失，请刷新页面后重试')
    return null
  }
  const impact = await previewOrderItemMutation(route.params.id as string, {
    operation: 'update',
    item_id: editingItemId.value!,
    item: itemMutationPayload(),
    reason: itemReason.value.trim(),
    expected_updated_at: order.value.updated_at,
  })
  itemPreview.value = impact
  return impact
}

async function handleSaveItem() {
  if (!editingItemId.value) {
    ElMessage.warning('请选择需要编辑的订单明细')
    return
  }
  if (!itemReason.value.trim()) {
    ElMessage.warning('请填写订单明细变更原因')
    return
  }
  itemSaving.value = true
  try {
    const impact = await previewCurrentItem()
    if (!impact) return
    if (!impact.can_apply) {
      ElMessage.warning(impact.lock_reasons.map(reason => reason.message).join('；') || '当前订单不可直接修改')
      return
    }
    const mutation: PendingItemMutation = {
      operation: 'update',
      itemId: editingItemId.value,
      data: itemMutationPayload(),
      reason: itemReason.value.trim(),
    }
    pendingMutation.value = mutation
    if (impact.requires_confirmation) {
      highRiskAcknowledged.value = false
      impactDialogVisible.value = true
      return
    }
    await applyItemMutation(impact, mutation)
  } catch (error: unknown) {
    ElMessage.error(mutationErrorMessage(error))
  } finally {
    itemSaving.value = false
  }
}

async function handleDeleteItem(item: OrderItemResponse) {
  if (!order.value?.updated_at) {
    ElMessage.error('订单版本信息缺失，请刷新页面后重试')
    return
  }
  try {
    const { value: reason } = await ElMessageBox.prompt(
      `删除「${item.item_name}」后将重新计算订单总额，且删除记录会写入审计日志。请输入删除原因。`,
      '删除订单明细',
      {
        confirmButtonText: '继续预检',
        cancelButtonText: '取消',
        inputPlaceholder: '例如：客户取消该制作项',
        inputValidator: (value) => value.trim() ? true : '请输入删除原因',
      },
    )
    const impact = await previewOrderItemMutation(route.params.id as string, {
      operation: 'delete',
      item_id: item.id,
      reason: reason.trim(),
      expected_updated_at: order.value.updated_at,
    })
    itemPreview.value = impact
    if (!impact.can_apply) {
      ElMessage.warning(impact.lock_reasons.map(lock => lock.message).join('；') || '当前订单不可删除明细')
      return
    }
    const mutation: PendingItemMutation = {
      operation: 'delete',
      itemId: item.id,
      reason: reason.trim(),
    }
    pendingMutation.value = mutation
    if (impact.requires_confirmation) {
      highRiskAcknowledged.value = false
      impactDialogVisible.value = true
      return
    }
    await ElMessageBox.confirm(
      `订单总额将从 ¥${impact.before.total_amount.toFixed(2)} 变为 ¥${impact.after.total_amount.toFixed(2)}。确定删除「${item.item_name}」吗？`,
      '确认删除订单明细',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' },
    )
    await applyItemMutation(impact, mutation)
  } catch (error: unknown) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(mutationErrorMessage(error))
  }
}

async function applyItemMutation(
  impact: OrderItemMutationImpactResponse,
  mutation: PendingItemMutation,
) {
  if (!order.value?.updated_at) throw new Error('订单版本信息缺失，请刷新页面后重试')
  const confirmation = {
    reason: mutation.reason,
    expected_updated_at: order.value.updated_at,
    preview_id: impact.preview_id,
    plan_hash: impact.plan_hash,
    preview_expires_at: impact.preview_expires_at,
    confirm_high_risk: highRiskAcknowledged.value,
  }
  const result = mutation.operation === 'delete'
    ? await deleteOrderItem(route.params.id as string, mutation.itemId!, confirmation)
    : await updateOrderItem(route.params.id as string, mutation.itemId!, { ...mutation.data, ...confirmation })
  order.value = result
  impactDialogVisible.value = false
  itemDialogVisible.value = false
  itemPreview.value = null
  pendingMutation.value = null
  highRiskAcknowledged.value = false
  let refreshFailed = false
  try {
    await Promise.all([fetchOrder(), fetchTasks()])
  } catch {
    refreshFailed = true
  }
  if (refreshFailed) {
    ElMessage.warning('订单变更已提交，但关联视图刷新失败，请手动刷新页面核对结果')
  }
  if (result.change_batch?.status === 'PENDING_ADJUSTMENT') {
    ElMessage.warning('订单已修改；部分关联事实已保留，差异已进入待复核/调整')
  } else {
    ElMessage.success(mutation.operation === 'delete' ? '订单明细已作废' : '订单明细已更新')
  }
}

async function confirmImpactAndApply() {
  if (!itemPreview.value || !pendingMutation.value) {
    ElMessage.warning('变更预检信息已失效，请重新预检')
    return
  }
  itemSaving.value = true
  try {
    await applyItemMutation(itemPreview.value, pendingMutation.value)
  } catch (error: unknown) {
    ElMessage.error(mutationErrorMessage(error))
  } finally {
    itemSaving.value = false
  }
}

function cancelImpactConfirmation() {
  impactDialogVisible.value = false
  itemPreview.value = null
  pendingMutation.value = null
  highRiskAcknowledged.value = false
}

function mutationErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message
  if (typeof error === 'string' && error) return error
  return '订单明细变更失败，请刷新后重试'
}

const designCompleted = computed(() => designTasks.value.filter(task => task.status === 'completed').length)
const productionCompleted = computed(() => productionTasks.value.filter(task => task.status === 'completed').length)
const installationCompleted = computed(() => installationTasks.value.filter(task => task.status === 'completed').length)

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

function statusLabel(s: string) {
  const map: Record<string, string> = {
    pending_confirm: '待确认', confirmed: '已确认', designing: '设计中',
    in_production: '生产中', in_installation: '安装中',
    completed: '已完成', cancelled: '已取消',
  }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending_confirm: 'warning', confirmed: 'info', designing: '', in_production: '', in_installation: '', completed: 'success', cancelled: 'danger' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

function mutationDecisionLabel(decision: string) {
  const map: Record<string, string> = {
    DIRECT_APPLY: '本次变更可直接应用',
    CONFIRM_AND_REFRESH: '确认后刷新可安全更新的关联项',
    APPROVAL_AND_ADJUSTMENT: '确认后修改，并保留事实生成差异/待调整项',
    BLOCK: '本次变更被阻断',
  }
  return map[decision] || decision
}

function mutationOperationLabel(operation: string) {
  return operation === 'add' ? '新增' : operation === 'update' ? '修改' : '作废'
}

function relationTypeLabel(type: string) {
  const map: Record<string, string> = {
    document: '订单级',
    item: '明细级',
    snapshot: '快照',
    source: '来源引用',
  }
  return map[type] || type
}

function relationStatusLabel(status?: string | null) {
  if (!status) return '-'
  const map: Record<string, string> = {
    draft: '草稿', pending: '待处理', confirmed: '已确认', accepted: '已验收',
    completed: '已完成', settled: '已结算', active: '有效', cancelled: '已取消',
    in_progress: '进行中', conditional: '有条件验收', out: '已出库', in: '已入库',
    rejected: '已驳回', approved: '已审批', dispatched: '已派车', returned: '已归还',
  }
  return map[status] || status
}

function relationActionLabel(action: string) {
  const map: Record<string, string> = {
    refresh_plan: '自动刷新执行计划',
    refresh_draft: '自动刷新草稿快照',
    refresh_plan_or_review: '刷新计划或标记复核',
    preserve_fact_and_reconcile: '保留事实并重新核对',
    preserve_fact_and_adjust: '保留事实并生成差异调整',
    preserve_fact_and_review: '保留事实并待复核',
    review_required: '必须人工复核',
  }
  return map[action] || action
}

function riskLabel(risk: string) {
  return risk === 'high' ? '高' : risk === 'medium' ? '中' : '低'
}

function riskTagType(risk: string) {
  return (risk === 'high' ? 'danger' : risk === 'medium' ? 'warning' : 'success') as 'success' | 'warning' | 'danger'
}

function designStatusLabel(s: string) { const m: Record<string, string> = { pending: '初始/待分配', pending_review: '待确认', completed: '已完成', cancelled: '已取消' }; return m[s] || s }
function designStatusColor(s: string) { const m: Record<string, string> = { pending: 'info', pending_review: 'warning', completed: 'success', cancelled: 'info' }; return (m[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined }
function prodStatusLabel(s: string) { const m: Record<string, string> = { pending: '待制作', queued: '排队中', in_progress: '制作中', qc_check: '待质检', rework: '返工', completed: '已完成', cancelled: '已取消' }; return m[s] || s }
function prodStatusColor(s: string) { const m: Record<string, string> = { pending: 'info', queued: 'warning', in_progress: '', qc_check: 'warning', rework: 'danger', completed: 'success', cancelled: 'info' }; return (m[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined }
function instStatusLabel(s: string) { const m: Record<string, string> = { pending: '待分配', assigned: '已分配', in_progress: '安装中', pending_acceptance: '待验收', completed: '已完成', cancelled: '已取消' }; return m[s] || s }
function instStatusColor(s: string) { const m: Record<string, string> = { pending: 'info', assigned: '', in_progress: 'warning', pending_acceptance: 'warning', completed: 'success', cancelled: 'info' }; return (m[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined }

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

async function fetchTasks() {
  tasksLoading.value = true
  try {
    const [d, p, i] = await Promise.all([
      getDesignTasks({ order_id: route.params.id as string, page_size: 100 }),
      getProductionTasks({ order_id: route.params.id as string, page_size: 100 }),
      getInstallationTasks({ order_id: route.params.id as string, page_size: 100 }),
    ])
    designTasks.value = d.items; productionTasks.value = p.items; installationTasks.value = i.items
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

onMounted(() => { fetchOrder(); fetchTasks() })
</script>

<style scoped>
.page { padding: 0; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.item-form :deep(.el-form-item) { margin-bottom: 14px; }
.impact-section-title { font-weight: 600; color: var(--ad-text); margin: 12px 0 8px; }
.amount-up { color: var(--el-color-success); }
.amount-down { color: var(--el-color-danger); }
:deep(.group-header-row) { background: var(--ad-bg-secondary, #f5f7fa) !important; }
:deep(.group-header-row td) { border-bottom: 2px solid var(--ad-primary, #409eff) !important; }
:deep(.group-total-row) { background: var(--ad-bg-secondary, #fafafa) !important; }
:deep(.group-total-row td) { border-top: 1px solid var(--ad-border, #dcdfe6) !important; font-weight: 600; }
</style>
