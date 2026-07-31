<template>
  <div class="page">
    <div class="page-header"><h2>考勤规则</h2><el-button type="danger" @click="openCreate">新建规则</el-button></div>
    <el-table :data="rules" v-loading="loading" stripe>
      <el-table-column prop="name" label="规则名称" width="160" />
      <el-table-column label="适用部门" width="120"><template #default="{row}">{{row.department||"全局"}}</template></el-table-column>
      <el-table-column prop="check_in_time" label="上班时间" width="100" />
      <el-table-column prop="check_out_time" label="下班时间" width="100" />
      <el-table-column prop="late_threshold" label="迟到阈值(min)" width="120" />
      <el-table-column prop="overtime_rate" label="加班费率" width="100" />
      <el-table-column label="启用" width="80"><template #default="{row}"><el-tag :type="row.is_active?'success':'info'" size="small">{{row.is_active?"是":"否"}}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{row}"><el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button><el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button></template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="showDialog" :title="isEditing?'编辑规则':'新建规则'" width="500px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="规则名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="适用部门"><el-select v-model="form.department" placeholder="留空=全局" clearable style="width:100%"><el-option label="设计部" value="design" /><el-option label="生产部" value="production" /><el-option label="安装部" value="installation" /><el-option label="销售部" value="sales" /><el-option label="财务部" value="finance" /><el-option label="行政部" value="admin" /></el-select></el-form-item>
        <el-form-item label="上班时间" required><el-time-picker v-model="form.check_in_time" format="HH:mm" value-format="HH:mm" style="width:100%" /></el-form-item>
        <el-form-item label="下班时间" required><el-time-picker v-model="form.check_out_time" format="HH:mm" value-format="HH:mm" style="width:100%" /></el-form-item>
        <el-form-item label="迟到阈值(分钟)"><el-input-number v-model="form.late_threshold" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="加班费率"><el-input-number v-model="form.overtime_rate" :min="1" :max="3" :step="0.1" style="width:100%" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from "vue"
import { getAttendanceRules, createAttendanceRule, updateAttendanceRule, deleteAttendanceRule, type AttendanceRuleItem } from "@/api/attendance"
import { ElMessage, ElMessageBox } from "element-plus"
const rules=ref<AttendanceRuleItem[]>([]); const loading=ref(false); const showDialog=ref(false); const isEditing=ref(false); const saving=ref(false)
const form=ref<Record<string, unknown>>({name:"",check_in_time:"09:00",check_out_time:"18:00",department:"",late_threshold:0,early_leave_threshold:0,overtime_rate:1.5,is_active:true})
async function fetchData(){loading.value=true;try{rules.value=(await getAttendanceRules())||[]}finally{loading.value=false}}
function openCreate(){isEditing.value=false;form.value={name:"",check_in_time:"09:00",check_out_time:"18:00",department:"",late_threshold:0,early_leave_threshold:0,overtime_rate:1.5,is_active:true};showDialog.value=true}
function openEdit(r:AttendanceRuleItem){isEditing.value=true;form.value={...r};showDialog.value=true}
async function handleSave(){saving.value=true;try{if(isEditing.value){await updateAttendanceRule(form.value.id as string,form.value)}else{await createAttendanceRule(form.value)};ElMessage.success(isEditing.value?"已更新":"已创建");showDialog.value=false;await fetchData()}finally{saving.value=false}}
async function handleDelete(r:AttendanceRuleItem){await ElMessageBox.confirm("确定删除？","提示",{type:"warning"});await deleteAttendanceRule(r.id);ElMessage.success("已删除");await fetchData()}
onMounted(fetchData)
</script>
