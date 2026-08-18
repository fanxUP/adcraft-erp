<template>
  <el-dialog
    :title="`模型管理 - ${provider.provider_name}`"
    v-model="visible"
    width="700px"
    @close="emit('close')"
   :close-on-click-modal="false">
    <div class="mb-12">
      <el-button size="small" @click="showAdd = true" type="danger">
        <el-icon><Plus /></el-icon>添加模型
      </el-button>
    </div>

    <el-table v-loading="loading" :data="models" stripe style="width: 100%">
      <el-table-column prop="display_name" label="显示名称" min-width="140" />
      <el-table-column prop="upstream_model_code" label="上游模型" min-width="140">
        <template #default="{ row }">
          <code style="font-size: 12px; background: var(--ad-darker); padding: 2px 6px; border-radius: 3px;">
            {{ row.upstream_model_code }}
          </code>
        </template>
      </el-table-column>
      <el-table-column prop="model_role" label="角色" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="roleTagType(row.model_role)" effect="plain">
            {{ row.model_role || '-' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="能力" width="160">
        <template #default="{ row }">
          <div class="caps">
            <el-tag v-if="row.supports_streaming" size="small" type="info">流</el-tag>
            <el-tag v-if="row.supports_tools" size="small" type="success">工具</el-tag>
            <el-tag v-if="row.supports_json_schema" size="small" type="warning">JSON</el-tag>
            <el-tag v-if="row.supports_vision" size="small" type="primary">视觉</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="enabled" label="启用" width="60">
        <template #default="{ row }">
          <el-switch
            :model-value="row.enabled"
            size="small"
            @change="(v: any) => toggleModel(row.id, Boolean(v))"
          />
        </template>
      </el-table-column>
      <el-table-column prop="context_window" label="上下文" width="90">
        <template #default="{ row }">
          {{ row.context_window ? (row.context_window / 1000).toFixed(0) + 'K' : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-popconfirm title="确认删除？" @confirm="removeModel(row.id)">
            <template #reference>
              <el-button text size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add model dialog -->
    <el-dialog
      title="添加模型"
      v-model="showAdd"
      width="480px"
      append-to-body
     :close-on-click-modal="false">
      <el-form ref="addFormRef" :model="addForm" label-width="120px" :rules="addRules">
        <el-form-item label="模型名称" prop="upstream_model_code">
          <el-input v-model="addForm.upstream_model_code" placeholder="如：deepseek-chat" />
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="addForm.display_name" placeholder="如：DeepSeek V3" />
        </el-form-item>
        <el-form-item label="模型角色">
          <el-select v-model="addForm.model_role" placeholder="选填" clearable style="width: 100%">
            <el-option label="标准 (standard)" value="standard" />
            <el-option label="快速 (fast)" value="fast" />
            <el-option label="推理 (reasoning)" value="reasoning" />
            <el-option label="视觉 (vision)" value="vision" />
            <el-option label="向量 (embedding)" value="embedding" />
          </el-select>
        </el-form-item>
        <el-form-item label="上下文长度">
          <el-input-number v-model="addForm.context_window" :min="0" :step="1024" style="width: 160px" />
        </el-form-item>
        <el-form-item label="能力">
          <el-checkbox v-model="addForm.supports_streaming">流式</el-checkbox>
          <el-checkbox v-model="addForm.supports_tools">工具调用</el-checkbox>
          <el-checkbox v-model="addForm.supports_json_schema">JSON Schema</el-checkbox>
          <el-checkbox v-model="addForm.supports_vision">图片理解</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button :loading="addLoading" @click="addModel" type="danger">添加</el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getModels,
  createModel,
  updateModel,
  deleteModel,
  type AIProviderItem,
  type AIModelItem,
  type ModelCreateData,
} from '@/api/ai-admin'
import { getErrorMessage } from '@/utils/error'

const props = defineProps<{ provider: AIProviderItem }>()
const emit = defineEmits<{ close: [] }>()

const visible = ref(true)
const loading = ref(false)
const models = ref<AIModelItem[]>([])
const showAdd = ref(false)
const addLoading = ref(false)
const addFormRef = ref()

const addForm = ref<ModelCreateData>({
  provider_id: props.provider.id,
  upstream_model_code: '',
  display_name: '',
  model_role: 'standard',
  context_window: null,
  supports_streaming: true,
  supports_tools: false,
  supports_json_schema: false,
  supports_vision: false,
})

const addRules = {
  upstream_model_code: [{ required: true, message: '请输入模型名称' }],
  display_name: [{ required: true, message: '请输入显示名称' }],
}

function roleTagType(role: string | null): '' | 'primary' | 'warning' | 'success' | 'info' {
  const map: Record<string, '' | 'primary' | 'warning' | 'success' | 'info'> = {
    fast: '', standard: 'primary', reasoning: 'warning', vision: 'success', embedding: 'info',
  }
  return map[role || ''] || ''
}

async function loadModels() {
  loading.value = true
  try {
    const res = await getModels({ provider_id: props.provider.id, page_size: 100 })
    models.value = res.items || []
  } catch {
    ElMessage.error('加载模型列表失败')
  } finally {
    loading.value = false
  }
}

async function toggleModel(id: string, enable: boolean) {
  try {
    await updateModel(id, { enabled: enable })
    await loadModels()
  } catch {
    ElMessage.error('操作失败')
  }
}

async function removeModel(id: string) {
  try {
    await deleteModel(id)
    await loadModels()
    ElMessage.success('已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

async function addModel() {
  if (!addFormRef.value) return
  try {
    await addFormRef.value.validate()
  } catch {
    return
  }
  addLoading.value = true
  try {
    await createModel({ ...addForm.value })
    ElMessage.success('模型已添加')
    showAdd.value = false
    await loadModels()
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, '添加失败'))
  } finally {
    addLoading.value = false
  }
}

onMounted(loadModels)
</script>

<style scoped>
.mb-12 { margin-bottom: 12px; }
.caps { display: flex; gap: 4px; flex-wrap: wrap; }
</style>
