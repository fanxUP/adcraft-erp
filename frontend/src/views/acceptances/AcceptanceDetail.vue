<template>
  <div class="page">
    <div class="page-header">
      <el-button text @click="$router.push('/acceptances')" style="font-size: 16px;">← 返回</el-button>
      <h2>{{ form.acceptance_no }}</h2>
      <div class="header-actions">
        <el-button
          v-if="form.status === 'draft'"
          type="primary" @click="handleSubmit"
        >提交验收</el-button>
        <el-button
          v-if="form.status === 'pending'"
          type="success" @click="handleAccept"
        >确认验收</el-button>
        <el-button
          v-if="form.status === 'pending'"
          type="danger" @click="handleReject"
        >驳回</el-button>
        <el-button
          v-if="form.status === 'rejected'"
          type="warning" @click="handleBackToDraft"
        >退回草稿</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <!-- 基本信息 -->
      <el-tab-pane label="基本信息" name="info">
        <!-- 订单信息头 — 编辑和只读模式均显示 -->
        <el-card class="order-info-card" v-if="form.order_id">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="订单编号">{{ form.order_no || '-' }}</el-descriptions-item>
            <el-descriptions-item label="客户名称">{{ form.customer_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="项目名称" :span="2">{{ form.project_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="联系人">{{ form.contact_person || '-' }}</el-descriptions-item>
            <el-descriptions-item label="联系电话">{{ form.contact_phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="客户地址" :span="2">{{ form.customer_address || '-' }}</el-descriptions-item>
            <el-descriptions-item label="部门/科室">{{ form.department || '-' }}</el-descriptions-item>
            <el-descriptions-item label="下单日期">{{ form.order_date?.slice(0, 10) || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
        <el-card class="order-info-card" v-else>
          <div style="color: var(--ad-text-secondary); text-align: center; padding: 16px;">
            独立验收单（未关联订单）
          </div>
        </el-card>

        <!-- 验收审批流程图 -->
        <AcceptanceWorkflow
          :current-status="form.status"
          :changing="statusChanging"
          @change="handleWorkflowChange"
        />

        <el-card style="margin-top: 16px;">
          <!-- 编辑模式：显示表单 -->
          <el-form v-if="canEdit" :model="form" label-width="140px">
            <el-form-item label="验收人/联系电话：">
              <el-input v-model="form.accepted_by" placeholder="验收人姓名/联系电话" />
            </el-form-item>
            <el-form-item label="负责人/联系电话：">
              <el-select v-model="form.our_acceptor_id" placeholder="选择负责人" clearable filterable>
                <el-option
                  v-for="u in userOptions"
                  :key="u.id"
                  :label="u.real_name || u.username"
                  :value="u.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="备注：">
              <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="备注" />
            </el-form-item>
            <el-form-item label="优惠金额：">
              <el-input-number v-model="form.discount_amount" :min="0" :precision="2" :controls="false" style="width: 200px" />
            </el-form-item>
            <el-form-item label="预付金额：">
              <el-input-number v-model="form.advance_amount" :min="0" :precision="2" :controls="false" style="width: 200px" />
            </el-form-item>
          </el-form>

          <!-- 详细信息（编辑/查看模式均显示） -->
          <el-descriptions :column="1" border :style="canEdit ? 'margin-top: 16px;' : ''">
            <el-descriptions-item label="状态：">
              <el-tag :type="statusColor(form.status)">{{ statusLabel(form.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="联系人：">{{ form.contact_person || '-' }}</el-descriptions-item>
            <el-descriptions-item label="联系电话：">{{ form.contact_phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="验收日期：">{{ form.accepted_at?.slice(0, 10) || '-' }}</el-descriptions-item>
            <el-descriptions-item label="验收人/联系电话：">{{ form.accepted_by || '-' }}</el-descriptions-item>
            <el-descriptions-item label="负责人/联系电话：">{{ form.our_acceptor_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="驳回原因：" v-if="form.reject_reason">
              <span style="color: var(--el-color-danger);">{{ form.reject_reason }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="备注：">{{ form.remark || '-' }}</el-descriptions-item>
            <el-descriptions-item label="优惠金额：">¥ {{ form.discount_amount?.toFixed(2) || '0.00' }}</el-descriptions-item>
            <el-descriptions-item label="预付金额：">¥ {{ form.advance_amount?.toFixed(2) || '0.00' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间：">{{ form.created_at?.slice(0, 16) }}</el-descriptions-item>
            <el-descriptions-item label="更新时间：">{{ form.updated_at?.slice(0, 16) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>

      <!-- 验收明细 -->
      <el-tab-pane label="验收明细" name="items">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>验收明细（{{ form.items.length }} 项）</span>
              <el-button v-if="form.items.length" type="success" size="small" @click="acceptAll">一键验收</el-button>
            </div>
          </template>

          <el-table :data="displayRows" border :row-class-name="rowClassName">
            <el-table-column label="序号" width="55">
              <template #default="{ row, $index }">
                <template v-if="row.type === 'item'">{{ itemIndex(row, $index) }}</template>
              </template>
            </el-table-column>
            <el-table-column label="项目内容" min-width="140">
              <template #default="{ row }">
                <template v-if="row.type === 'group-header'">
                  <span style="font-weight: 600;">分项：{{ row.groupName }}</span>
                </template>
                <template v-else-if="row.type === 'group-total'">
                  <span style="font-weight: 600; float: right;">分项合计</span>
                </template>
                <template v-else>
                  <el-input v-if="canEdit" v-model="row.item.item_name" placeholder="项目内容" />
                  <span v-else>{{ row.item.item_name }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="材质工艺" min-width="120">
              <template #default="{ row }">
                <template v-if="row.type === 'item'">
                  <el-input v-if="canEdit" v-model="row.item.material_process" placeholder="材质工艺" />
                  <span v-else>{{ row.item.material_process || '-' }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="规格" min-width="120">
              <template #default="{ row }">
                <template v-if="row.type === 'item'">
                  <el-input v-if="canEdit" v-model="row.item.specification" placeholder="规格" />
                  <span v-else>{{ row.item.specification || '-' }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="面积" width="80">
              <template #default="{ row }">
                <template v-if="row.type === 'item'">{{ row.item.area != null ? row.item.area.toFixed(2) : '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column label="数量" width="80">
              <template #default="{ row }">
                <template v-if="row.type === 'item'">
                  <el-input-number v-if="canEdit" v-model="row.item.quantity" :min="0" :precision="2" size="small" controls-position="right" />
                  <span v-else>{{ row.item.quantity ?? '-' }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="单位" width="70">
              <template #default="{ row }">
                <template v-if="row.type === 'item'">
                  <el-input v-if="canEdit" v-model="row.item.unit" placeholder="单位" />
                  <span v-else>{{ row.item.unit || '-' }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="单价" width="90">
              <template #default="{ row }">
                <template v-if="row.type === 'item'">
                  <el-input-number v-if="canEdit" v-model="row.item.unit_price" :min="0" :precision="2" size="small" controls-position="right" />
                  <span v-else>{{ row.item.unit_price != null ? row.item.unit_price.toFixed(2) : '-' }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="小计" width="100">
              <template #default="{ row }">
                <template v-if="row.type === 'item'">
                  <el-input-number v-if="canEdit" v-model="row.item.subtotal" :min="0" :precision="2" size="small" controls-position="right" />
                  <span v-else>{{ row.item.subtotal != null ? row.item.subtotal.toFixed(2) : '-' }}</span>
                </template>
                <template v-else-if="row.type === 'group-total'"><strong>¥ {{ row.total.toFixed(2) }}</strong></template>
              </template>
            </el-table-column>
            <el-table-column label="样图" width="90">
              <template #default="{ row }">
                <template v-if="row.type === 'item'">
                  <div v-if="row.item.image_url" style="display: flex; align-items: center; gap: 4px;">
                    <el-image :src="row.item.image_url" :preview-src-list="[row.item.image_url]" fit="cover" style="width: 32px; height: 32px; border-radius: 4px; cursor: pointer;" />
                    <el-button v-if="canEdit" text type="danger" size="small" @click="row.item.image_url = ''" style="padding: 0;">×</el-button>
                  </div>
                  <el-upload v-else-if="canEdit" :show-file-list="false" :http-request="(opt: any) => handleImageUpload(opt, row.item)" accept="image/*" style="display: inline;">
                    <el-button text type="primary" size="small" style="padding: 0;">上传</el-button>
                  </el-upload>
                  <span v-else style="color: #999">-</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="备注" min-width="100">
              <template #default="{ row }">
                <template v-if="row.type === 'item'">
                  <el-input v-if="canEdit" v-model="row.item.remark" placeholder="备注" />
                  <span v-else>{{ row.item.remark || '-' }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="验收结果" width="100">
              <template #default="{ row }">
                <template v-if="row.type === 'item'">
                  <el-select v-model="row.item.item_status" size="small">
                    <el-option label="待验收" value="pending" />
                    <el-option label="通过" value="accepted" />
                    <el-option label="不通过" value="rejected" />
                    <el-option label="有条件通过" value="conditional" />
                  </el-select>
                </template>
              </template>
            </el-table-column>
          </el-table>

          <!-- 明细合计 -->
          <div v-if="form.items?.length" style="margin-top: 16px; padding-top: 12px; border-top: 2px solid var(--ad-primary, #409eff); text-align: right;">
            <div style="font-size: 16px; font-weight: 600; color: var(--ad-text); margin-bottom: 6px;">
              明细合计：¥ {{ itemsTotal.toFixed(2) }}
            </div>
            <div style="font-size: 13px; color: var(--ad-text-secondary);">
              大写金额：{{ toChineseAmount(itemsTotal) }}
            </div>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- 附件 -->
      <el-tab-pane label="附件" name="attachments">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>验收照片 / 附件</span>
              <el-upload
                :show-file-list="false"
                :http-request="handleUpload"
                accept="image/*,.pdf,.doc,.docx"
              >
                <el-button type="primary" size="small">上传附件</el-button>
              </el-upload>
            </div>
          </template>

          <el-table :data="form.attachments" border>
            <el-table-column prop="filename" label="文件名" min-width="200" />
            <el-table-column label="大小" width="100">
              <template #default="{ row }">
                {{ row.filesize ? (row.filesize / 1024).toFixed(1) + ' KB' : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="downloadFile(row)">下载</el-button>
                <el-button text type="danger" size="small" @click="deleteAtt(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 保存按钮 -->
    <div class="save-bar" v-if="canEdit">
      <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      <el-button @click="$router.push('/acceptances')">取消</el-button>
    </div>

    <!-- 驳回原因弹框 -->
    <el-dialog v-model="rejectDialogVisible" title="驳回验收" width="400px" :close-on-click-modal="false">
      <el-form>
        <el-form-item label="驳回原因" required>
          <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="请填写驳回原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject" :loading="statusChanging">确认驳回</el-button>
      </template>
    </el-dialog>

    <div v-if="form.status === 'accepted' || form.status === 'rejected' || form.status === 'draft' || form.status === 'pending'" style="text-align: left; margin-top: 24px;">
      <el-button type="primary" @click="showPrint = true">
        <el-icon><Printer /></el-icon> 打印预览
      </el-button>
    </div>

    <AcceptancePrint
      :visible="showPrint"
      :acceptance-id="String(route.params.id)"
      @close="showPrint = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Printer } from '@element-plus/icons-vue'
import {
  getAcceptance, updateAcceptance,
  changeAcceptanceStatus, uploadAcceptanceAttachment, deleteAcceptanceAttachment
} from '@/api/acceptances'
import { uploadAttachment } from '@/api/tasks'
import { getUsers } from '@/api/users'
import type {
  AcceptanceDetailResponse, AcceptanceAttachmentResponse,
  AcceptanceItemResponse, UserResponse
} from '@/types/api'
import AcceptancePrint from './AcceptancePrint.vue'
import AcceptanceWorkflow from './AcceptanceWorkflow.vue'

const route = useRoute()
const activeTab = ref('info')
const saving = ref(false)
const statusChanging = ref(false)
const showPrint = ref(false)
const rejectDialogVisible = ref(false)
const rejectReason = ref('')

const canEdit = computed(() => form.status === 'draft' || form.status === 'rejected' || route.query.edit === '1')

const itemsTotal = computed(() => form.items.reduce((s, i) => s + (i.subtotal || 0), 0))

type DisplayRow =
  | { type: 'group-header'; groupName: string }
  | { type: 'item'; item: AcceptanceItemResponse; groupName: string }
  | { type: 'group-total'; groupName: string; total: number }

const displayRows = computed<DisplayRow[]>(() => {
  const grouped = new Map<string, AcceptanceItemResponse[]>()
  const ungrouped: AcceptanceItemResponse[] = []
  for (const item of form.items) {
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
    const total = groupItems.reduce((s, i) => s + (i.subtotal || 0), 0)
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

function acceptAll() {
  form.items.forEach(item => { item.item_status = 'accepted' })
  ElMessage.success('已全部设为通过')
}

async function handleImageUpload(opt: { file: File }, item: AcceptanceItemResponse) {
  try {
    const res = await uploadAttachment('acceptance_item', item.id || form.id, opt.file, 'image')
    item.image_url = `/uploads/${res.file_path}`
    ElMessage.success('上传成功')
  } catch {
    ElMessage.error('上传失败')
  }
}

function itemIndex(row: DisplayRow, displayIdx: number): number {
  let count = 0
  for (let i = 0; i <= displayIdx; i++) {
    if (displayRows.value[i].type === 'item') count++
  }
  return count
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
        if (unitIdx === 0 && bigUnits[bigIdx]) { result += bigUnits[bigIdx]; zeroFlag = false }
      } else {
        if (zeroFlag) { result += '零'; zeroFlag = false }
        result += digits[d] + units[unitIdx]
        if (unitIdx === 0 && bigUnits[bigIdx]) result += bigUnits[bigIdx]
      }
    }
    result += '元'
  }
  if (jiao === 0 && fen === 0) { result += '整' }
  else {
    if (jiao > 0) result += digits[jiao] + '角'
    else if (intPart > 0) result += '零'
    if (fen > 0) result += digits[fen] + '分'
  }
  return (negative ? '负' : '') + result
}

const form = reactive<AcceptanceDetailResponse>({
  id: '',
  acceptance_no: '',
  order_id: '',
  order_no: '',
  customer_name: '',
  project_name: '',
  contact_person: '',
  contact_phone: '',
  status: 'draft',
  accepted_at: undefined,
  accepted_by: '',
  our_acceptor_id: '',
  our_acceptor_name: '',
  remark: '',
  reject_reason: '',
  discount_amount: 0,
  advance_amount: 0,
  created_at: '',
  updated_at: '',
  items: [],
  attachments: [],
})

const userOptions = ref<UserResponse[]>([])

async function loadUsers() {
  try {
    const data = await getUsers({ page: 1, page_size: 100 })
    userOptions.value = data.items || data
  } catch { /* ignore */ }
}

async function handleSave() {
  saving.value = true
  try {
    const payload = {
      accepted_by: form.accepted_by || null,
      our_acceptor_id: form.our_acceptor_id || null,
      remark: form.remark || null,
      discount_amount: form.discount_amount || 0,
      advance_amount: form.advance_amount || 0,
      items: form.items.map((item) => ({
        item_name: item.item_name,
        material_process: item.material_process || null,
        specification: item.specification || null,
        area: item.area ?? null,
        quantity: item.quantity || null,
        unit: item.unit || null,
        unit_price: item.unit_price ?? null,
        subtotal: item.subtotal ?? null,
        image_url: item.image_url || null,
        order_item_id: item.order_item_id || null,
        remark: item.remark || null,
        item_status: item.item_status,
        group_name: item.group_name || null,
      })),
    }
    await updateAcceptance(form.id, payload)
    ElMessage.success('保存成功')
    loadDetail(form.id)
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleSubmit() {
  await ElMessageBox.confirm('确定提交验收？提交后将无法编辑。', '提示')
  await changeAcceptanceStatus(form.id, { to_status: 'pending' })
  ElMessage.success('已提交验收')
  loadDetail(form.id)
}

async function handleWorkflowChange(toStatus: string) {
  if (toStatus === 'pending') {
    await ElMessageBox.confirm('确定提交验收？提交后将无法编辑。', '提示')
    statusChanging.value = true
    try {
      await changeAcceptanceStatus(form.id, { to_status: 'pending' })
      ElMessage.success('已提交验收')
      loadDetail(form.id)
    } finally { statusChanging.value = false }
  } else if (toStatus === 'accepted') {
    const { value } = await ElMessageBox.prompt('请输入客户签收人（可选）', '确认验收', {
      inputPlaceholder: '签收人姓名',
      confirmButtonText: '确认验收',
      cancelButtonText: '取消',
      inputValue: form.accepted_by || '',
    })
    statusChanging.value = true
    try {
      await changeAcceptanceStatus(form.id, { to_status: 'accepted', accepted_by: value || null })
      ElMessage.success('已确认验收')
      loadDetail(form.id)
    } finally { statusChanging.value = false }
  } else if (toStatus === 'rejected') {
    rejectReason.value = ''
    rejectDialogVisible.value = true
  } else if (toStatus === 'draft') {
    await ElMessageBox.confirm('确定退回草稿？退回后可重新编辑。', '提示')
    statusChanging.value = true
    try {
      await changeAcceptanceStatus(form.id, { to_status: 'draft' })
      ElMessage.success('已退回草稿')
      loadDetail(form.id)
    } finally { statusChanging.value = false }
  }
}

async function handleAccept() {
  const { value } = await ElMessageBox.prompt('请输入客户签收人（可选）', '确认验收', {
    inputPlaceholder: '签收人姓名',
    confirmButtonText: '确认验收',
    cancelButtonText: '取消',
    inputValue: form.accepted_by || '',
  })
  await changeAcceptanceStatus(form.id, { to_status: 'accepted', accepted_by: value || null })
  ElMessage.success('已确认验收')
  loadDetail(form.id)
}

function handleReject() {
  rejectReason.value = ''
  rejectDialogVisible.value = true
}

async function confirmReject() {
  if (!rejectReason.value.trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  statusChanging.value = true
  try {
    await changeAcceptanceStatus(form.id, { to_status: 'rejected', reason: rejectReason.value })
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    loadDetail(form.id)
  } finally {
    statusChanging.value = false
  }
}

async function handleBackToDraft() {
  await ElMessageBox.confirm('确定退回草稿？退回后可重新编辑。', '提示')
  await changeAcceptanceStatus(form.id, { to_status: 'draft' })
  ElMessage.success('已退回草稿')
  loadDetail(form.id)
}

async function handleUpload(options: { file: File }) {
  try {
    await uploadAcceptanceAttachment(form.id, options.file)
    ElMessage.success('上传成功')
    loadDetail(form.id)
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '上传失败')
  }
}

async function deleteAtt(att: AcceptanceAttachmentResponse) {
  await ElMessageBox.confirm('确定删除该附件？', '提示')
  await deleteAcceptanceAttachment(form.id, att.id)
  ElMessage.success('已删除')
  loadDetail(form.id)
}

function downloadFile(att: AcceptanceAttachmentResponse) {
  window.open(att.filepath, '_blank')
}

async function loadDetail(id: string) {
  const data = await getAcceptance(id)
  Object.assign(form, data)
}

const statusLabel = (s: string) => {
  const map: Record<string, string> = { draft: '草稿', pending: '待验收', accepted: '已验收', rejected: '已驳回' }
  return map[s] || s
}
const statusColor = (s: string): '' | 'success' | 'warning' | 'info' | 'danger' => {
  const map: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = { draft: 'info', pending: 'warning', accepted: 'success', rejected: 'danger' }
  return map[s] || ''
}

onMounted(async () => {
  await loadUsers()
  await loadDetail(route.params.id as string)
})

watch(() => route.params.id, async (newId) => {
  if (newId && route.name === 'AcceptanceDetail') {
    await loadDetail(newId as string)
  }
})
</script>

<style scoped>
.page { padding: 20px; }
.page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); flex: 1; }
.header-actions { display: flex; gap: 8px; }
.save-bar { margin-top: 20px; display: flex; gap: 12px; }
.order-info-card { margin-bottom: 0; }
.order-info-card :deep(.el-descriptions__title) { font-size: 14px; font-weight: 600; }
:deep(.group-header-row) { background: var(--ad-bg-secondary, #f5f7fa) !important; }
:deep(.group-header-row td) { border-bottom: 2px solid var(--ad-primary, #409eff) !important; }
:deep(.group-total-row) { background: var(--ad-bg-secondary, #fafafa) !important; }
:deep(.group-total-row td) { border-top: 1px solid var(--ad-border, #dcdfe6) !important; font-weight: 600; }
</style>
