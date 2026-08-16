<template>
  <div class="page">
    <div class="page-header">
      <h2>{{ isEdit ? '编辑报价（CDR）' : '新建报价（CDR）' }}</h2>
      <div>
        <el-button @click="$router.back()">返回</el-button>
        <el-button type="danger" @click="handleSave" :loading="saving">保存版本</el-button>
      </div>
    </div>

    <!-- ── 设计文件上传 / SVG 解析 / AI 辅助 ── -->
    <el-card shadow="never" class="section-card" style="margin-top:16px">
      <template #header>
        <span>设计文件</span>
      </template>
      <div v-if="!route.params.id" style="color:var(--ad-text-secondary);font-size:13px">保存报价后可上传设计文件</div>
      <template v-else>
        <el-upload
          :show-file-list="false"
          :before-upload="(f:any)=>{onFileUpload({target:{files:[f]}} as any);return false}"
          accept=".cdr,.svg,.pdf,.ai,.eps,.dxf,.png,.jpg,.jpeg"
        >
          <el-button type="primary" :loading="uploading" size="small">上传设计文件</el-button>
          <span style="margin-left:8px;font-size:12px;color:var(--ad-text-secondary)">支持 .cdr .svg .pdf .ai .eps .dxf .png .jpg</span>
        </el-upload>

        <div v-if="uploadList.length" style="margin-top:8px">
          <div v-for="att in uploadList" :key="att.id" style="display:flex;align-items:center;gap:8px;padding:4px 0">
            <span>{{ att.filename }}</span>
            <el-tag size="small">{{ att.file_type }}</el-tag>
            <el-button text type="primary" size="small" @click="handleParseSvg(att.id)" :disabled="att.file_type!=='svg'">解析 SVG</el-button>
            <el-button text type="danger" size="small" @click="deleteFile(att.id)">删除</el-button>
          </div>
        </div>

        <!-- SVG 解析结果 -->
        <div v-if="parseResult" style="margin-top:8px;background:#f5f7fa;padding:8px;border-radius:4px">
          <div style="font-weight:bold;margin-bottom:4px">SVG 解析结果</div>
          <div style="font-size:13px">页面: {{ parseResult.document_width_mm }}mm x {{ parseResult.document_height_mm }}mm</div>
          <div v-for="(s,i) in parseResult.shapes" :key="i" style="font-size:13px">{{ s.label }} ({{ s.area_m2 }} m²)</div>
          <el-button size="small" type="success" style="margin-top:4px" @click="applyParsedShapes">应用为报价明细</el-button>
        </div>

        <!-- AI 辅助 -->
        <div style="margin-top:12px">
          <el-input
            v-model="aiDescription"
            type="textarea"
            :rows="2"
            placeholder="输入需求描述，AI 将根据已上传文件生成报价明细，例如：5米宽2米高户外广告牌，不锈钢边框，UV打印"
          />
          <div style="margin-top:4px;display:flex;gap:8px">
            <el-button type="success" :loading="aiLoading" size="small" @click="handleAiAssist">AI 智能生成</el-button>
            <el-button v-if="aiResult" size="small" type="warning" @click="applyAiSuggestion">应用 AI 建议</el-button>
          </div>
          <div v-if="aiLoading" style="font-size:13px;color:var(--ad-text-secondary);margin-top:4px">AI 正在生成报价明细...</div>
        </div>
      </template>
    </el-card>

    <!-- 基本信息 -->
    <el-card shadow="never" class="section-card">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="报价单号">
              <el-input v-model="form.quote_no" disabled />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="客户">
              <el-select v-model="form.customer_id" filterable clearable style="width: 100%">
                <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="项目名称" required>
              <el-input v-model="form.project_name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="税率">
              <el-input-number v-model="form.tax_rate" :min="0" :max="30" :precision="1" style="width: 150px">
                <template #suffix>%</template>
              </el-input-number>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="联系人">
              <el-select v-model="form.contact_person" filterable allow-create default-first-option clearable autocomplete="off" placeholder="选择联系人或输入" style="width: 100%" @change="handleContactChange" @clear="form.contact_phone = ''">
                <el-option v-for="c in contactOptions" :key="c.id" :label="c.name" :value="c.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系电话">
              <el-input v-model="form.contact_phone" autocomplete="off" placeholder="手机/电话" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- 报价明细 -->
    <el-card shadow="never" class="section-card" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>报价明细</span>
          <el-button text type="primary" @click="addLine">+ 添加行</el-button>
        </div>
      </template>

      <el-table :data="lines" stripe border scrollbar-always-on>
        <el-table-column label="#" width="50">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column label="项目内容" min-width="160">
          <template #default="{ row }">
            <el-input v-model="row.item_name" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="产品/材质/工艺" min-width="280">
          <template #default="{ row, $index }">
            <el-input
              v-model="row.material_process"
              size="small"
              placeholder="点击选择产品/材质/工艺"
              @click="openProductPicker(row, $index)"
              clearable
              @clear="row.use_area = false; row.quantity = 1; row.product_id = ''"
            />
          </template>
        </el-table-column>
        <el-table-column label="宽" width="170">
          <template #default="{ row, $index }">
            <div class="dimension-field">
              <el-input-number v-model="row.width" :precision="2" :min="0" size="small" :controls="false" @change="onDimensionChange(row, $index)" />
              <el-select v-model="row.width_unit" size="small" @change="onDimensionChange(row, $index)">
                <el-option v-for="unit in dimensionUnits" :key="unit" :label="unit" :value="unit" />
              </el-select>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="高" width="170">
          <template #default="{ row, $index }">
            <div class="dimension-field">
              <el-input-number v-model="row.height" :precision="2" :min="0" size="small" :controls="false" @change="onDimensionChange(row, $index)" />
              <el-select v-model="row.height_unit" size="small" @change="onDimensionChange(row, $index)">
                <el-option v-for="unit in dimensionUnits" :key="unit" :label="unit" :value="unit" />
              </el-select>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="件数" width="70">
          <template #default="{ row, $index }">
            <el-input-number v-model="row.pieces" :precision="0" :min="1" size="small" :controls="false" @change="onDimensionChange(row, $index)" />
          </template>
        </el-table-column>
        <el-table-column label="面积" width="130">
          <template #default="{ row, $index }">
            <div class="area-field">
              <span>{{ calcQuoteLineArea(row).toFixed(2) }}</span>
              <el-switch v-model="row.use_area" size="small" @change="onAreaToggle(row, $index)" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="90">
          <template #default="{ row, $index }">
            <el-input-number v-model="row.quantity" :precision="2" :min="0.01" :disabled="row.use_area" size="small" :controls="false" @change="onLineChange($index)" />
          </template>
        </el-table-column>
        <el-table-column label="单位" width="100">
          <template #default="{ row }">
            <el-select v-model="row.unit" filterable allow-create size="small" placeholder="选择/输入">
              <el-option v-for="unit in quoteUnits" :key="unit" :label="unit" :value="unit" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="单价" width="120">
          <template #default="{ row }">
            <el-input-number v-model="row.unit_price" :min="0" :precision="2" size="small" :controls="false" />
          </template>
        </el-table-column>
        <el-table-column label="小计" width="120">
          <template #default="{ row }">¥{{ calcQuoteLineSubtotal(row).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="样图" width="90">
          <template #default="{ row }">
            <div v-if="row.image_url" class="image-field">
              <el-image :src="row.image_url" :preview-src-list="[row.image_url]" fit="cover" />
              <el-button text type="danger" size="small" @click="row.image_url = ''">×</el-button>
            </div>
            <el-upload v-else :show-file-list="false" :http-request="(opt: any) => handleImageUpload(opt, row)" accept="image/*">
              <el-button text type="primary" size="small">上传</el-button>
            </el-upload>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="120">
          <template #default="{ row }">
            <el-input v-model="row.remark" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="60" fixed="right">
          <template #default="{ $index }">
            <el-button text type="danger" size="small" @click="lines.splice($index, 1)">×</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 汇总 -->
    <el-card shadow="never" class="section-card" style="margin-top: 16px">
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="summary-item">
            <span class="label">小计</span>
            <span class="value">¥{{ summary.subtotal }}</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <span class="label">预估成本</span>
            <span class="value cost">¥{{ summary.cost }}</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <span class="label">税费</span>
            <span class="value">¥{{ summary.tax }}</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item highlight">
            <span class="label">合计</span>
            <span class="value">¥{{ summary.total }}</span>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 规则执行明细 -->
    <el-card shadow="never" class="section-card" style="margin-top: 16px" v-if="pricingTrace.length">
      <template #header>
        <span>规则执行明细</span>
      </template>
      <el-timeline>
        <el-timeline-item
          v-for="(step, i) in pricingTrace"
          :key="i"
          :timestamp="step.rule_code"
        >
          <p>{{ step.description }}</p>
          <p v-if="step.output_value" class="trace-detail">
            输出：{{ JSON.stringify(step.output_value) }}
          </p>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <!-- 备注 -->
    <el-card shadow="never" class="section-card" style="margin-top: 16px">
      <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="备注" />
    </el-card>
  </div>
    <!-- 产品选择面板 -->
    <ProductPickerDialog v-model="productPickerVisible" :customer-id="form.customer_id" @selected="onProductPicked" @updated="onProductUpdated" />
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { uploadAttachment } from '@/api/tasks'
import { getCustomer } from '@/api/customers'
import { calculatePricing, createCDRQuote, createQuoteVersion, getLatestVersion, getCDRQuote,
  uploadDesignFile, listDesignAttachments, deleteDesignAttachment,
  parseSvgAttachment, aiAssistFromDescription,
  type AiAssistResult,
  type DesignAttachment,
  type PricingResult,
  type PricingTraceStep,
  type QuoteLineProcessInput,
  type SvgParseResult,
} from '@/api/cdrQuote'
import type {
  CustomerResponse,
  ContactResponse,
  PaginatedData,
  ProductResponse,
} from '@/types/api'
import { getErrorMessage } from '@/utils/error'
import { applyProductMaterialProcess, formatProductMaterialProcess } from '@/utils/productMaterialProcess'
import {
  calcQuoteLineArea,
  calcQuoteLineSubtotal,
  dimensionToMillimeters,
  syncQuoteLineAreaQuantity,
} from '@/utils/quoteLineCalculation'
import ProductPickerDialog from '@/components/ProductPickerDialog.vue'

interface EditorLine {
  product_id: string
  material_id: string
  item_name: string
  material_process: string
  width?: number
  width_unit: string
  height?: number
  height_unit: string
  pieces: number
  use_area: boolean
  quantity: number
  unit: string
  unit_price: number
  other_fee: number
  amount: number
  cost: number
  remark: string
  image_url: string
  group_name?: string
  processes: QuoteLineProcessInput[]
}

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const saving = ref(false)

const customers = ref<CustomerResponse[]>([])
const contactOptions = ref<ContactResponse[]>([])
const productPickerVisible = ref(false)
const pendingPickerLine = ref<EditorLine | null>(null)
const pendingPickerIndex = ref(-1)
const pricingTrace = ref<PricingTraceStep[]>([])
const dimensionUnits = ['m', 'cm', 'mm']
const quoteUnits = ['㎡', 'm', '个', '套', '块', '件', '批', '次', '组', '台']

const form = reactive({
  quote_no: '',
  customer_id: '',
  project_name: '',
  tax_rate: 6,
  contact_person: '',
  contact_phone: '',
  notes: '',
})

const lines = ref<EditorLine[]>([createEmptyLine()])
const calcResults = ref<Record<number, PricingResult>>({})

// 设计文件上传 / SVG / AI
const uploadList = ref<DesignAttachment[]>([])
const uploading = ref(false)
const parseResult = ref<SvgParseResult | null>(null)
const parseLoading = ref(false)
const aiDescription = ref('')
const aiLoading = ref(false)
const aiResult = ref<AiAssistResult | null>(null)

function createEmptyLine(): EditorLine {
  return {
    product_id: '',
    material_id: '',
    item_name: '',
    material_process: '',
    width: undefined,
    width_unit: 'm',
    height: undefined,
    height_unit: 'm',
    pieces: 1,
    use_area: false,
    quantity: 1,
    unit: '',
    unit_price: 0,
    other_fee: 0,
    amount: 0,
    cost: 0,
    remark: '',
    image_url: '',
    processes: [],
  }
}

const summary = computed(() => {
  let subtotal = 0, cost = 0
  lines.value.forEach((l, i) => {
    const r = calcResults.value[i]
    subtotal += calcQuoteLineSubtotal(l)
    cost += r ? Number(r.total_cost || 0) : Number(l.cost || 0)
  })
  const tax = subtotal * form.tax_rate / 100
  return {
    subtotal: subtotal.toFixed(2),
    cost: cost.toFixed(2),
    tax: tax.toFixed(2),
    total: (subtotal + tax).toFixed(2),
  }
})

async function fetchLookups() {
  try {
    const custRes = await api.get<PaginatedData<CustomerResponse>>('/customers/')
    customers.value = custRes.items || []
  } catch { /* ignore */ }
}

// 联系人下拉：加载所选客户的已存联系人（客户管理里添加的）
async function loadCustomerContacts(customerId: string) {
  const isExisting = customers.value.some(c => c.id === customerId)
  if (!customerId || !isExisting) {
    contactOptions.value = []
    return
  }
  try {
    const customer = await getCustomer(customerId)
    contactOptions.value = customer.contacts || []
  } catch {
    contactOptions.value = []
  }
}

function handleContactChange(name: string) {
  const c = contactOptions.value.find(c => c.name === name)
  if (c?.phone) form.contact_phone = c.phone
}

watch(() => form.customer_id, (val) => {
  if (!val) {
    contactOptions.value = []
    return
  }
  void loadCustomerContacts(String(val))
})

async function onLineChange(index: number) {
  const line = lines.value[index]
  if (!line.product_id) return

  try {
    const result = await calculatePricing({
      product_id: line.product_id,
      material_id: line.material_id || undefined,
      quantity: line.use_area ? line.pieces : line.quantity,
      width_mm: line.width ? dimensionToMillimeters(line.width, line.width_unit) : undefined,
      height_mm: line.height ? dimensionToMillimeters(line.height, line.height_unit) : undefined,
      customer_id: form.customer_id || undefined,
      tax_rate: form.tax_rate,
    })
    calcResults.value[index] = result
    line.unit_price = Number(result.unit_price || 0)
    line.amount = calcQuoteLineSubtotal(line)
    line.cost = Number(result.total_cost || 0)

    // 更新规则执行明细（取第一行明细）
    if (index === 0) {
      pricingTrace.value = result.pricing_trace || []
    }
  } catch (error: unknown) {
    ElMessage.warning(getErrorMessage(error, '计算失败'))
  }
}




function openProductPicker(line: EditorLine, index: number) {
  if (!form.customer_id) {
    ElMessage.warning('请先选择客户')
    return
  }
  pendingPickerLine.value = line
  pendingPickerIndex.value = index
  productPickerVisible.value = true
}

function onProductPicked(product: ProductResponse) {
  const line = pendingPickerLine.value
  const index = pendingPickerIndex.value
  if (!line) return
  onProductSelect(line, { value: formatProductMaterialProcess(product), product }, index)
  onLineChange(index)
  pendingPickerLine.value = null
  pendingPickerIndex.value = -1
}

function onProductUpdated(product: ProductResponse) {
  const line = pendingPickerLine.value
  const index = pendingPickerIndex.value
  if (!line || !line.product_id || line.product_id !== product.id) return
  // 产品主数据在选产品弹窗里被编辑后，同步到当前行；只更新产品继承字段，不改数量/面积开关
  Object.assign(line, applyProductMaterialProcess(line, product))
  onLineChange(index)
}

function onProductSelect(line: EditorLine, opt: { value: string; product: ProductResponse }, index: number) {
  Object.assign(line, applyProductMaterialProcess(line, opt.product))
  line.material_process = opt.value
  if (opt.product.pricing_method === 'area') {
    if (!line.use_area) {
      line.use_area = true
      syncQuoteLineAreaQuantity(line)
    }
  } else {
    line.use_area = false
    line.quantity = 1
  }
  onLineChange(index)
}

function onDimensionChange(line: EditorLine, index: number) {
  syncQuoteLineAreaQuantity(line)
  onLineChange(index)
}

function onAreaToggle(line: EditorLine, index: number) {
  if (line.use_area) {
    syncQuoteLineAreaQuantity(line)
  } else {
    line.quantity = 1
    line.unit = ''
  }
  onLineChange(index)
}

function addLine() {
  lines.value.push(createEmptyLine())
}

async function handleSave() {
  if (!form.project_name) {
    ElMessage.warning('请填写项目名称')
    return
  }

  saving.value = true
  try {
    // 1. 创建或获取报价
    let quoteId = route.params.id as string
    if (!quoteId) {
      const newQuote = await createCDRQuote({
        project_name: form.project_name,
        customer_id: form.customer_id || undefined,
        customer_name: customers.value.find(c => c.id === form.customer_id)?.name,
        tax_rate: form.tax_rate / 100,
        status: 'draft',
      })
      quoteId = newQuote.id
    }

    // 2. 创建版本
    const versionData = {
      contact_person: form.contact_person || undefined,
      contact_phone: form.contact_phone || undefined,
      notes: form.notes,
      lines: lines.value.map((l, index) => ({
        product_id: l.product_id,
        material_id: l.material_id || undefined,
        item_name: l.item_name || '待填写',
        material_process: l.material_process || undefined,
        width: l.width,
        width_unit: l.width_unit,
        height: l.height,
        height_unit: l.height_unit,
        pieces: l.pieces,
        use_area: l.use_area,
        quantity: l.quantity,
        unit: l.unit || undefined,
        unit_price: l.unit_price,
        other_fee: l.other_fee,
        remark: l.remark || undefined,
        image_url: l.image_url || undefined,
        sort_order: index,
        group_name: l.group_name,
        processes: l.processes || [],
      })),
    }

    await createQuoteVersion(quoteId, versionData)
    ElMessage.success('保存成功')
    router.push(`/cdr/quotes/${quoteId}`)
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function handleImageUpload(opt: { file: File }, line: EditorLine) {
  if (!route.params.id) {
    ElMessage.warning('请先保存报价再上传样图')
    return
  }
  try {
    const result = await uploadAttachment('cdr_quote_item', route.params.id as string, opt.file, 'image')
    line.image_url = `/uploads/${result.file_path}`
    ElMessage.success('上传成功')
  } catch {
    ElMessage.error('上传失败')
  }
}

async function onFileUpload(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  if (!route.params.id) {
    ElMessage.warning('请先保存报价再上传文件')
    return
  }
  uploading.value = true
  const file = input.files[0]
  try {
    await uploadDesignFile(route.params.id as string, file)
    ElMessage.success('上传成功: ' + file.name)
    await loadAttachments()
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, '上传失败'))
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function loadAttachments() {
  if (!route.params.id) return
  uploadList.value = (await listDesignAttachments(route.params.id as string)) || []
}

async function deleteFile(attId: string) {
  try {
    await deleteDesignAttachment(attId)
    uploadList.value = uploadList.value.filter(a => a.id !== attId)
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, '删除失败'))
  }
}

async function handleParseSvg(attId: string) {
  parseLoading.value = true
  parseResult.value = null
  try {
    const res = await parseSvgAttachment(attId)
    parseResult.value = res
    ElMessage.success('解析完成，规格 ' + res.shape_count + ' 个')
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, '解析失败'))
  } finally {
    parseLoading.value = false
  }
}

async function handleAiAssist() {
  if (!aiDescription.value.trim()) {
    ElMessage.warning('请输入需求描述')
    return
  }
  if (!route.params.id) {
    ElMessage.warning('请先保存报价')
    return
  }
  aiLoading.value = true
  aiResult.value = null
  try {
    const res = await aiAssistFromDescription(route.params.id as string, aiDescription.value)
    aiResult.value = res
    ElMessage.success('生成完成')
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, 'AI 请求失败'))
  } finally {
    aiLoading.value = false
  }
}

async function applyAiSuggestion() {
  if (!aiResult.value?.ai_suggestions) return
  const suggestions = aiResult.value.ai_suggestions
  const items = Array.isArray(suggestions) ? suggestions : (suggestions.items || suggestions.lines || [])
  for (const item of items) {
    const line = createEmptyLine()
    line.item_name = item.description || item.item_name || ''
    line.width = item.width_mm ? Number(item.width_mm) : undefined
    line.width_unit = 'mm'
    line.height = item.height_mm ? Number(item.height_mm) : undefined
    line.height_unit = 'mm'
    line.quantity = Number(item.quantity || 1)
    lines.value.push(line)
  }
  ElMessage.success('已应用 ' + items.length + ' 条明细')
}

async function applyParsedShapes() {
  if (!parseResult.value?.shapes) return
  for (const s of parseResult.value.shapes) {
    const line = createEmptyLine()
    line.item_name = s.label
    line.width = s.width_mm || undefined
    line.width_unit = 'mm'
    line.height = s.height_mm || undefined
    line.height_unit = 'mm'
    line.quantity = s.quantity || 1
    lines.value.push(line)
  }
  ElMessage.success('已应用 ' + parseResult.value.shapes.length + ' 个图形')
}

onMounted(async () => {
  await fetchLookups()

  if (isEdit.value) {
    try {
      const quote = await getCDRQuote(route.params.id as string)
      if (quote) {
        form.quote_no = quote.quote_no || quote.doc_no || ''
        form.customer_id = quote.customer_id || ''
        form.project_name = quote.project_name || ''
        form.tax_rate = Number(quote.tax_rate) * 100 || 6
      }
      const version = await getLatestVersion(route.params.id as string)
      form.contact_person = version?.contact_person || ''
      form.contact_phone = version?.contact_phone || ''
      if (version?.lines?.length) {
        lines.value = version.lines.map((l) => ({
          product_id: l.product_id || '',
          material_id: l.material_id || '',
          item_name: l.item_name || l.description,
          material_process: l.material_process || '',
          width: l.width ? Number(l.width) : (l.width_mm ? Number(l.width_mm) : undefined),
          width_unit: l.width_unit || (l.width_mm ? 'mm' : 'm'),
          height: l.height ? Number(l.height) : (l.height_mm ? Number(l.height_mm) : undefined),
          height_unit: l.height_unit || (l.height_mm ? 'mm' : 'm'),
          pieces: Number(l.pieces || 1),
          use_area: Boolean(l.use_area),
          quantity: Number(l.quantity || 1),
          unit: l.unit || '',
          unit_price: Number(l.unit_price || 0),
          other_fee: Number(l.other_fee || 0),
          amount: Number(l.amount || 0),
          cost: Number(l.estimated_cost || 0),
          remark: l.remark || '',
          image_url: l.image_url || '',
          group_name: l.group_name,
          processes: l.processes.map((process) => ({
            process_id: process.process_id,
            billing_quantity: Number(process.billing_quantity),
            unit_price: Number(process.unit_price),
          })),
        }))
      }
    } catch { /* ignore */ }
    await loadAttachments()
  }
})
</script>

<style scoped>
.section-card { margin-bottom: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.summary-item { text-align: center; padding: 12px; }
.summary-item .label { display: block; font-size: 13px; color: var(--ad-text-secondary); margin-bottom: 4px; }
.summary-item .value { font-size: 22px; font-weight: 700; color: var(--ad-text); }
.summary-item .value.cost { color: var(--el-color-warning); }
.summary-item.highlight .value { color: var(--ad-red); }
.trace-detail { font-size: 12px; color: var(--ad-text-secondary); word-break: break-all; }
.stacked-field { display: flex; flex-direction: column; gap: 4px; }
.dimension-field { display: grid; grid-template-columns: 90px 65px; gap: 4px; align-items: center; }
.area-field { display: flex; align-items: center; justify-content: space-between; gap: 4px; }
.image-field { display: flex; align-items: center; gap: 4px; }
.image-field :deep(.el-image) { width: 32px; height: 32px; border-radius: 4px; }

/* 出现横向滚动时，滚动条始终可见，且与最后一行、表格底部边框保持间距 */
:deep(.el-table.el-table--scrollable-x .el-scrollbar__view) { padding-bottom: 12px; }
:deep(.el-table.el-table--scrollable-x .el-table__body-wrapper) { margin-bottom: 8px; }
</style>
