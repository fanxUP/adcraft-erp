<template>
  <div class="page">
    <div class="page-header"><h2>高空车人员</h2><el-button type="primary" @click="handleCreate">+ 新增人员</el-button></div>
    <div class="search-bar">
      <el-input v-model="keyword" placeholder="姓名/手机号搜索" clearable style="width: 200px" @keyup.enter="fetchData" />
      <el-button type="primary" @click="fetchData">搜索</el-button>
    </div>
    <el-table :data="list" stripe v-loading="loading">
      <el-table-column prop="name" label="姓名" width="240" />
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column label="性别" width="70"><template #default="{ row }">{{ GENDER_LABELS[row.gender as string] || row.gender || '-' }}</template></el-table-column>
      <el-table-column prop="ethnicity" label="族别" width="100"><template #default="{ row }">{{ row.ethnicity || '-' }}</template></el-table-column>
      <el-table-column prop="license_no" label="驾驶证号" width="140" />
      <el-table-column prop="license_type" label="驾照类型" width="100" />
      <el-table-column prop="license_expire_date" label="驾照到期" width="110">
        <template #default="{ row }"><span :style="{ color: isExpiredSoon(row.license_expire_date) ? '#f56c6c' : '' }">{{ row.license_expire_date || '-' }}</span></template>
      </el-table-column>
      <el-table-column prop="is_external" label="外协" width="80">
        <template #default="{ row }"><el-tag :type="row.is_external ? 'warning' : 'info'" size="small">{{ row.is_external ? '外协' : '内部' }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">{{ row.status === 'active' ? '在职' : '停用' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button link :type="row.status === 'active' ? 'danger' : 'success'" size="small" @click="handleToggle(row)">{{ row.status === 'active' ? '停用' : '启用' }}</el-button>
          <el-popconfirm title="确定删除该人员？" @confirm="handleDelete(row)">
            <template #reference>
              <el-button link type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, prev, pager, next" style="margin-top: 16px" @current-change="fetchData" />

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑人员' : '新增人员'" width="560px" destroy-on-close @closed="attachments = []" :close-on-click-modal="false">
      <el-form :model="form" label-width="90px">
        <el-form-item label="姓名" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="性别"><el-select v-model="form.gender" clearable style="width: 100%"><el-option v-for="g in GENDER_OPTIONS" :key="g.value" :label="g.label" :value="g.value" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="族别"><el-select v-model="form.ethnicity" clearable filterable style="width: 100%"><el-option v-for="e in ETHNICITY_OPTIONS" :key="e.value" :label="e.label" :value="e.value" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="驾驶证号"><el-input v-model="form.license_no" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="驾照类型"><el-input v-model="form.license_type" placeholder="A1/B2/C1等" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="驾照到期"><el-date-picker v-model="form.license_expire_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" /></el-form-item></el-col>
        </el-row>
        <el-divider content-position="left">身份证信息</el-divider>
        <el-form-item label="身份证号"><el-input v-model="form.id_card_no" placeholder="18 位身份证号" /></el-form-item>
        <el-form-item label="身份证正面">
          <div class="idcard-slot">
            <el-upload :http-request="(o: any) => handleUploadIdCard(o, 'front')" :show-file-list="false" accept="image/*">
              <el-button size="small" type="primary" plain>上传照片</el-button>
            </el-upload>
            <template v-if="form.id_card_front_url">
              <el-image :src="form.id_card_front_url" :preview-src-list="[form.id_card_front_url]" preview-teleported fit="cover" class="idcard-preview" />
              <el-button size="small" type="danger" link @click="form.id_card_front_url = ''">移除</el-button>
            </template>
            <span v-else class="idcard-tip">未上传</span>
          </div>
        </el-form-item>
        <el-form-item label="身份证反面">
          <div class="idcard-slot">
            <el-upload :http-request="(o: any) => handleUploadIdCard(o, 'back')" :show-file-list="false" accept="image/*">
              <el-button size="small" type="primary" plain>上传照片</el-button>
            </el-upload>
            <template v-if="form.id_card_back_url">
              <el-image :src="form.id_card_back_url" :preview-src-list="[form.id_card_back_url]" preview-teleported fit="cover" class="idcard-preview" />
              <el-button size="small" type="danger" link @click="form.id_card_back_url = ''">移除</el-button>
            </template>
            <span v-else class="idcard-tip">未上传</span>
          </div>
        </el-form-item>
        <el-divider content-position="left">银行卡信息</el-divider>
        <el-form-item label="银行卡号"><el-input v-model="form.bank_card_no" placeholder="银行卡号" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="开户行"><el-input v-model="form.bank_name" placeholder="如：工商银行" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="户名"><el-input v-model="form.bank_account_name" placeholder="持卡人姓名" /></el-form-item></el-col>
        </el-row>
        <template v-if="editingId">
          <el-divider content-position="left">附件</el-divider>
          <div class="att-upload-row">
            <el-select v-model="attCategory" style="width: 120px">
              <el-option v-for="(label, val) in ATT_TYPE_LABELS" :key="val" :label="label" :value="val" />
            </el-select>
            <el-upload :http-request="handleUploadAttachment" :show-file-list="false" :disabled="attUploading">
              <el-button type="primary" plain size="small" :loading="attUploading">上传附件</el-button>
            </el-upload>
          </div>
          <div v-if="attachments.length" class="att-list">
            <el-tag v-for="att in attachments" :key="att.id" :type="ATT_TYPE_TAGS[att.attachment_type] || 'info'" closable @close="handleDeleteAttachment(att.id)">
              <a :href="att.file_url" target="_blank" class="att-link">{{ ATT_TYPE_LABELS[att.attachment_type] || att.attachment_type }}·{{ att.file_name }}</a>
            </el-tag>
          </div>
          <div v-else style="color: var(--ad-text-secondary); font-size: 13px">暂无附件</div>
        </template>
        <el-form-item label="外协人员"><el-switch v-model="form.is_external" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import {
  getAerialPersonnel,
  createAerialPersonnel,
  updateAerialPersonnel,
  deleteAerialPersonnel,
  uploadAerialPersonnelImage,
  getAerialPersonnelAttachments,
  createAerialPersonnelAttachment,
  deleteAerialPersonnelAttachment,
  type AerialPersonnel,
  type AerialPersonnelAttachment,
} from '@/api/aerial'
import { getErrorMessage } from '@/utils/error'
import { GENDER_OPTIONS, ETHNICITY_OPTIONS } from '@/config/ethnicity'
import { ATTACHMENT_TYPE_LABELS, ATTACHMENT_TYPE_TAGS } from '@/config/attachment'

const loading = ref(false); const saving = ref(false); const dialogVisible = ref(false)
const list = ref<AerialPersonnel[]>([]); const total = ref(0); const page = ref(1); const pageSize = ref(20)
const keyword = ref(''); const editingId = ref<string | null>(null)
const GENDER_LABELS: Record<string, string> = Object.fromEntries(GENDER_OPTIONS.map((g) => [g.value, g.label]))

const form = reactive({
  name: '', phone: '', gender: '', ethnicity: '', license_no: '', license_type: '', license_expire_date: '', is_external: false, remark: '',
  id_card_no: '', id_card_front_url: '', id_card_back_url: '',
  bank_card_no: '', bank_name: '', bank_account_name: '',
})

// 附件
const attachments = ref<AerialPersonnelAttachment[]>([])
const attCategory = ref('other')
const attUploading = ref(false)
const ATT_TYPE_LABELS = ATTACHMENT_TYPE_LABELS
const ATT_TYPE_TAGS = ATTACHMENT_TYPE_TAGS

async function fetchData() {
  loading.value = true
  try { const res = await getAerialPersonnel({ keyword: keyword.value, page: page.value, page_size: pageSize.value }); list.value = res.items || []; total.value = res.total || 0 }
  catch (error: unknown) { ElMessage.error(getErrorMessage(error)) } finally { loading.value = false }
}

function handleCreate() {
  editingId.value = null
  attachments.value = []
  Object.assign(form, { name: '', phone: '', gender: '', ethnicity: '', license_no: '', license_type: '', license_expire_date: '', is_external: false, remark: '', id_card_no: '', id_card_front_url: '', id_card_back_url: '', bank_card_no: '', bank_name: '', bank_account_name: '' })
  dialogVisible.value = true
}

async function handleEdit(row: AerialPersonnel) {
  editingId.value = row.id
  attachments.value = []
  Object.assign(form, {
    name: row.name, phone: row.phone, gender: row.gender || '', ethnicity: row.ethnicity || '', license_no: row.license_no, license_type: row.license_type,
    license_expire_date: row.license_expire_date, is_external: row.is_external, remark: row.remark,
    id_card_no: row.id_card_no || '', id_card_front_url: row.id_card_front_url || '', id_card_back_url: row.id_card_back_url || '',
    bank_card_no: row.bank_card_no || '', bank_name: row.bank_name || '', bank_account_name: row.bank_account_name || '',
  })
  dialogVisible.value = true
  try { attachments.value = (await getAerialPersonnelAttachments(row.id)) || [] } catch (e: unknown) { ElMessage.error(getErrorMessage(e)) }
}

async function handleSave() {
  if (!form.name.trim()) return ElMessage.warning('请填写姓名')
  saving.value = true
  try {
    if (editingId.value) {
      await updateAerialPersonnel(editingId.value, form)
      ElMessage.success('修改成功')
      dialogVisible.value = false
      fetchData()
    } else {
      const r = await createAerialPersonnel(form)
      editingId.value = r.id
      attachments.value = (await getAerialPersonnelAttachments(r.id)) || []
      ElMessage.success('已新增，可继续上传附件')
    }
  } catch (error: unknown) { ElMessage.error(getErrorMessage(error)) } finally { saving.value = false }
}

async function handleToggle(row: AerialPersonnel) {
  const newStatus = row.status === 'active' ? 'disabled' : 'active'
  try { await ElMessageBox.confirm(`确定${newStatus === 'disabled' ? '停用' : '启用'} ${row.name}？`, '确认'); await updateAerialPersonnel(row.id, { status: newStatus }); ElMessage.success('操作成功'); fetchData() } catch {}
}

async function handleDelete(row: AerialPersonnel) {
  try { await deleteAerialPersonnel(row.id); ElMessage.success('删除成功'); fetchData() } catch (error: unknown) { ElMessage.error(getErrorMessage(error)) }
}

// ── 身份证正反面照片上传 ───────────────────────────────────────────────────
async function handleUploadIdCard(options: { file: File }, slot: 'front' | 'back') {
  try {
    const res = await uploadAerialPersonnelImage(options.file)
    if (slot === 'front') form.id_card_front_url = res.file_url
    else form.id_card_back_url = res.file_url
    ElMessage.success('照片已上传')
  } catch (error: unknown) { ElMessage.error(getErrorMessage(error)) }
}

// ── 附件上传/删除 ──────────────────────────────────────────────────────────
async function handleUploadAttachment(options: UploadRequestOptions) {
  if (!editingId.value) return
  attUploading.value = true
  try {
    await createAerialPersonnelAttachment(editingId.value, options.file, attCategory.value)
    ElMessage.success('上传成功')
    attachments.value = (await getAerialPersonnelAttachments(editingId.value)) || []
  } catch (error: unknown) { ElMessage.error(getErrorMessage(error)) } finally { attUploading.value = false }
}

async function handleDeleteAttachment(aid: string) {
  try { await ElMessageBox.confirm('确定删除该附件？', '确认') } catch { return }
  try {
    await deleteAerialPersonnelAttachment(aid)
    ElMessage.success('删除成功')
    if (editingId.value) attachments.value = (await getAerialPersonnelAttachments(editingId.value)) || []
  } catch (error: unknown) { ElMessage.error(getErrorMessage(error)) }
}

function isExpiredSoon(d: string | null) { if (!d) return false; return new Date(d) <= new Date(Date.now() + 30 * 86400000) }

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.search-bar { display: flex; gap: 8px; margin-bottom: 16px; }
.idcard-slot { display: flex; align-items: center; gap: 10px; width: 100%; }
.idcard-preview { width: 70px; height: 46px; border-radius: 4px; border: 1px solid var(--ad-border); }
.idcard-tip { color: var(--ad-text-secondary); font-size: 13px; }
.att-upload-row { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }
.att-list { display: flex; flex-wrap: wrap; gap: 8px; }
.att-link { text-decoration: none; }
</style>
