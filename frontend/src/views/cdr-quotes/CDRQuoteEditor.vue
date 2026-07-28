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
      <div v-if="!route.params.id" style="color:#909399;font-size:13px">保存报价后可上传设计文件</div>
      <template v-else>
        <el-upload
          :show-file-list="false"
          :before-upload="(f:any)=>{onFileUpload({target:{files:[f]}} as any);return false}"
          accept=".cdr,.svg,.pdf,.ai,.eps,.dxf,.png,.jpg,.jpeg"
        >
          <el-button type="primary" :loading="uploading" size="small">上传设计文件</el-button>
          <span style="margin-left:8px;font-size:12px;color:#909399">支持 .cdr .svg .pdf .ai .eps .dxf .png .jpg</span>
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
          <div v-if="aiLoading" style="font-size:13px;color:#909399;margin-top:4px">AI 正在生成报价明细...</div>
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

      <el-table :data="lines" stripe highlight-current-row>
        <el-table-column label="#" width="50">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column label="产品" width="150">
          <template #default="{ row, $index }">
            <el-select v-model="row.product_id" filterable size="small" @change="onLineChange($index)">
              <el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="材料" width="150">
          <template #default="{ row, $index }">
            <el-select v-model="row.material_id" filterable size="small" clearable @change="onLineChange($index)">
              <el-option v-for="m in materials" :key="m.id" :label="m.name" :value="m.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="描述" min-width="150">
          <template #default="{ row }">
            <el-input v-model="row.description" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="宽(mm)" width="90">
          <template #default="{ row, $index }">
            <el-input-number v-model="row.width_mm" :min="0" size="small" controls-position="right" style="width: 80px" @change="onLineChange($index)" />
          </template>
        </el-table-column>
        <el-table-column label="高(mm)" width="90">
          <template #default="{ row, $index }">
            <el-input-number v-model="row.height_mm" :min="0" size="small" controls-position="right" style="width: 80px" @change="onLineChange($index)" />
          </template>
        </el-table-column>
        <el-table-column label="数量" width="80">
          <template #default="{ row, $index }">
            <el-input-number v-model="row.quantity" :min="1" size="small" controls-position="right" style="width: 70px" @change="onLineChange($index)" />
          </template>
        </el-table-column>
        <el-table-column label="单价" width="100">
          <template #default="{ row }">
            <el-input-number v-model="row.unit_price" :min="0" :precision="2" size="small" controls-position="right" style="width: 90px" />
          </template>
        </el-table-column>
        <el-table-column label="金额" width="100">
          <template #default="{ row }">¥{{ Number(row.amount || 0).toFixed(2) }}</template>
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
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { calculatePricing, createQuoteVersion, getLatestVersion, getCDRQuote,
  uploadDesignFile, listDesignAttachments, deleteDesignAttachment,
  parseSvgAttachment, aiAssistFromDescription } from '@/api/cdrQuote'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const saving = ref(false)

const customers = ref<any[]>([])
const products = ref<any[]>([])
const materials = ref<any[]>([])
const pricingTrace = ref<any[]>([])

const form = reactive({
  quote_no: '',
  customer_id: '',
  project_name: '',
  tax_rate: 6,
  notes: '',
})

const lines = ref<any[]>([createEmptyLine()])
const calcResults = ref<Record<number, any>>({})

// 设计文件上传 / SVG / AI
const uploadList = ref<any[]>([])
const uploading = ref(false)
const parseResult = ref<any>(null)
const parseLoading = ref(false)
const aiDescription = ref('')
const aiLoading = ref(false)
const aiResult = ref<any>(null)

function createEmptyLine() {
  return {
    product_id: '',
    material_id: '',
    description: '',
    width_mm: 0,
    height_mm: 0,
    quantity: 1,
    unit_price: 0,
    amount: 0,
    cost: 0,
    processes: [],
  }
}

const summary = computed(() => {
  let subtotal = 0, cost = 0
  lines.value.forEach((l, i) => {
    const r = calcResults.value[i]
    subtotal += r ? Number(r.subtotal_amount || 0) : Number(l.amount || 0)
    cost += r ? Number(r.total_cost || 0) : 0
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
    const [custRes, prodRes, matRes] = await Promise.all([
      api.get<{ items: any[] }>('/customers/'),
      api.get<{ items: any[] }>('/products/'),
      api.get<{ items: any[] }>('/materials/'),
    ])
    customers.value = custRes?.items || custRes || []
    products.value = prodRes?.items || prodRes || []
    materials.value = matRes?.items || matRes || []
  } catch { /* ignore */ }
}

async function onLineChange(index: number) {
  const line = lines.value[index]
  if (!line.product_id) return

  try {
    const result = await calculatePricing({
      product_id: line.product_id,
      material_id: line.material_id || undefined,
      quantity: line.quantity,
      width_mm: line.width_mm || undefined,
      height_mm: line.height_mm || undefined,
      customer_id: form.customer_id || undefined,
      tax_rate: form.tax_rate,
    })
    calcResults.value[index] = result
    line.unit_price = Number(result.unit_price || 0)
    line.amount = Number(result.subtotal_amount || 0)
    line.cost = Number(result.total_cost || 0)

    // 更新规则执行明细（取第一行明细）
    if (index === 0) {
      pricingTrace.value = result.pricing_trace || []
    }
  } catch (e: any) {
    ElMessage.warning(e.message || '计算失败')
  }
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
      const newQuote = await api.post<{ id: string }>('/quotes/', {
        doc_type: 'quote',
        project_name: form.project_name,
        customer_id: form.customer_id || undefined,
        customer_name: customers.value.find(c => c.id === form.customer_id)?.name,
        status: 'draft',
      })
      quoteId = newQuote.id
    }

    // 2. 创建版本
    const versionData = {
      notes: form.notes,
      lines: lines.value.map(l => ({
        product_id: l.product_id,
        material_id: l.material_id || undefined,
        description: l.description || (products.value.find(p => p.id === l.product_id)?.name || ''),
        width_mm: l.width_mm || undefined,
        height_mm: l.height_mm || undefined,
        quantity: l.quantity,
        processes: l.processes || [],
      })),
    }

    await createQuoteVersion(quoteId, versionData)
    ElMessage.success('保存成功')
    router.push(`/cdr/quotes/${quoteId}`)
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
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
  } catch (e: any) {
    ElMessage.error(e.message || '上传失败')
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
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

async function handleParseSvg(attId: string) {
  parseLoading.value = true
  parseResult.value = null
  try {
    const res = await parseSvgAttachment(attId)
    parseResult.value = res
    ElMessage.success('解析完成，规格 ' + res.shape_count + ' 个')
  } catch (e: any) {
    ElMessage.error(e.message || '解析失败')
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
  } catch (e: any) {
    ElMessage.error(e.message || 'AI 请求失败')
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
    line.description = item.description || item.item_name || ''
    line.width_mm = Number(item.width_mm || 0)
    line.height_mm = Number(item.height_mm || 0)
    line.quantity = Number(item.quantity || 1)
    lines.value.push(line)
  }
  ElMessage.success('已应用 ' + items.length + ' 条明细')
}

async function applyParsedShapes() {
  if (!parseResult.value?.shapes) return
  for (const s of parseResult.value.shapes) {
    const line = createEmptyLine()
    line.description = s.label
    line.width_mm = s.width_mm || 0
    line.height_mm = s.height_mm || 0
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
      if (version?.lines?.length) {
        lines.value = version.lines.map((l: any) => ({
          product_id: l.product_id,
          material_id: l.material_id,
          description: l.description,
          width_mm: Number(l.width_mm || 0),
          height_mm: Number(l.height_mm || 0),
          quantity: Number(l.quantity || 1),
          unit_price: Number(l.unit_price || 0),
          amount: Number(l.amount || 0),
          cost: Number(l.estimated_cost || 0),
          processes: l.processes || [],
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
</style>
