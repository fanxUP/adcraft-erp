<template>
  <div class="page">
    <div class="page-header"><h2>安全检查</h2></div>

    <el-form :inline="true" style="margin-bottom: 16px">
      <el-form-item label="台账">
        <el-select v-model="selectedLedgerId" filterable remote :remote-method="searchLedgers" placeholder="输入台账编号搜索" style="width: 260px" @change="loadChecks">
          <el-option v-for="l in ledgerOptions" :key="l.id" :label="`${l.ledger_no} - ${l.work_location}`" :value="l.id" />
        </el-select>
      </el-form-item>
      <el-button type="primary" @click="showAddDialog = true" :disabled="!selectedLedgerId">+ 新增检查</el-button>
    </el-form>

    <el-table :data="checks" stripe v-loading="loading">
      <el-table-column prop="check_type" label="类型" width="100">
        <template #default="{ row }">{{ row.check_type === 'before_work' ? '出车前' : '收车后' }}</template>
      </el-table-column>
      <el-table-column prop="check_result" label="结果" width="80">
        <template #default="{ row }">
          <el-tag :type="row.check_result === 'passed' ? 'success' : 'danger'" size="small">{{ row.check_result === 'passed' ? '通过' : row.check_result === 'failed' ? '不通过' : '需注意' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="车辆外观" width="80"><template #default="{ row }"><el-tag :type="row.vehicle_appearance_ok ? 'success' : 'danger'" size="small">{{ row.vehicle_appearance_ok ? '正常' : '异常' }}</el-tag></template></el-table-column>
      <el-table-column label="轮胎" width="70"><template #default="{ row }"><el-tag :type="row.tire_ok ? 'success' : 'danger'" size="small">{{ row.tire_ok ? '正常' : '异常' }}</el-tag></template></el-table-column>
      <el-table-column label="液压系统" width="80"><template #default="{ row }"><el-tag :type="row.hydraulic_system_ok ? 'success' : 'danger'" size="small">{{ row.hydraulic_system_ok ? '正常' : '异常' }}</el-tag></template></el-table-column>
      <el-table-column label="支腿" width="70"><template #default="{ row }"><el-tag :type="row.outriggers_ok ? 'success' : 'danger'" size="small">{{ row.outriggers_ok ? '正常' : '异常' }}</el-tag></template></el-table-column>
      <el-table-column label="作业平台" width="80"><template #default="{ row }"><el-tag :type="row.platform_ok ? 'success' : 'danger'" size="small">{{ row.platform_ok ? '正常' : '异常' }}</el-tag></template></el-table-column>
      <el-table-column label="安全带" width="70"><template #default="{ row }"><el-tag :type="row.safety_belt_ok ? 'success' : 'danger'" size="small">{{ row.safety_belt_ok ? '正常' : '异常' }}</el-tag></template></el-table-column>
      <el-table-column prop="issue_description" label="异常说明" min-width="150" show-overflow-tooltip />
      <el-table-column prop="checked_at" label="检查时间" width="170" />
    </el-table>

    <el-empty v-if="!loading && checks.length === 0 && selectedLedgerId" description="暂无安全检查记录" />

    <el-dialog v-model="showAddDialog" title="新增安全检查" width="700px" destroy-on-close>
      <el-form :model="checkForm" label-width="100px">
        <el-form-item label="检查类型" required>
          <el-radio-group v-model="checkForm.check_type">
            <el-radio value="before_work">出车前检查</el-radio>
            <el-radio value="after_work">收车后检查</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-divider content-position="left">检查项目</el-divider>
        <el-row :gutter="16">
          <el-col :span="8" v-for="item in checkItems" :key="item.key">
            <el-form-item :label="item.label">
              <el-switch v-model="checkForm[item.key]" active-text="正常" inactive-text="异常" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="异常说明"><el-input v-model="checkForm.issue_description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showAddDialog = false">取消</el-button><el-button type="primary" @click="handleSaveCheck" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAerialSafetyChecks, createAerialSafetyCheck, getAerialLedgers } from '@/api/aerial'

const loading = ref(false); const saving = ref(false); const showAddDialog = ref(false)
const selectedLedgerId = ref('')
const ledgerOptions = ref<any[]>([])
const checks = ref<any[]>([])

const checkItems = [
  { key: 'vehicle_appearance_ok', label: '车辆外观' }, { key: 'tire_ok', label: '轮胎' },
  { key: 'brake_ok', label: '刹车' }, { key: 'light_ok', label: '灯光' },
  { key: 'hydraulic_system_ok', label: '液压系统' }, { key: 'outriggers_ok', label: '支腿' },
  { key: 'platform_ok', label: '作业平台' }, { key: 'safety_belt_ok', label: '安全带' },
  { key: 'warning_equipment_ok', label: '警示设备' }, { key: 'extinguisher_ok', label: '灭火器' },
  { key: 'documents_ok', label: '证件有效' }, { key: 'weather_ok', label: '天气适宜' },
  { key: 'site_risk_ok', label: '现场安全' },
]

const checkForm = reactive({
  check_type: 'before_work',
  vehicle_appearance_ok: true, tire_ok: true, brake_ok: true, light_ok: true,
  hydraulic_system_ok: true, outriggers_ok: true, platform_ok: true,
  safety_belt_ok: true, warning_equipment_ok: true, extinguisher_ok: true,
  documents_ok: true, weather_ok: true, site_risk_ok: true,
  issue_description: '',
})

async function searchLedgers(query: string) {
  if (!query) return
  try { const res = await getAerialLedgers({ keyword: query, page_size: 20 }); ledgerOptions.value = res.items || [] } catch {}
}

async function loadChecks() {
  if (!selectedLedgerId.value) return
  loading.value = true
  try { checks.value = await getAerialSafetyChecks({ ledger_id: selectedLedgerId.value }) || [] }
  catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}

async function handleSaveCheck() {
  saving.value = true
  try {
    await createAerialSafetyCheck({ ...checkForm, ledger_id: selectedLedgerId.value })
    ElMessage.success('检查记录已保存'); showAddDialog.value = false; loadChecks()
  } catch (e: any) { ElMessage.error(e.message) } finally { saving.value = false }
}
</script>

<style scoped>.page-header { margin-bottom: 16px; }</style>
