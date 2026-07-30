<template>
  <div class="page">
    <div class="page-header"><h2>员工履历</h2>
      <div style="display:flex;gap:8px;align-items:center">
        <el-select v-model="fEmp" placeholder="员工" clearable filterable style="width:200px" @change="fetchData">
          <el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" />
        </el-select>
        <el-select v-model="fType" placeholder="变动类型" clearable style="width:130px" @change="fetchData">
          <el-option label="入职" value="hire" /><el-option label="晋升" value="promotion" /><el-option label="调岗" value="transfer" /><el-option label="离职" value="resignation" />
        </el-select>
        <el-button type="danger" @click="openCreate">新增记录</el-button>
      </div>
    </div>
    <el-table :data="list" v-loading="loading" stripe style="width:100%">
      <el-table-column label="员工" width="150"><template #default="{row}">{{row.employee_name||row.employee_id}}</template></el-table-column>
      <el-table-column prop="change_date" label="变动日期" width="120" />
      <el-table-column label="变动类型" width="100"><template #default="{row}"><el-tag :type="typeColor(row.change_type)" size="small">{{typeLabel(row.change_type)}}</el-tag></template></el-table-column>
      <el-table-column label="原部门" width="110"><template #default="{row}">{{row.previous_department||"-"}}</template></el-table-column>
      <el-table-column label="新部门" width="110"><template #default="{row}">{{row.new_department||"-"}}</template></el-table-column>
      <el-table-column label="原职位" width="120"><template #default="{row}">{{row.previous_position||"-"}}</template></el-table-column>
      <el-table-column label="新职位" width="120"><template #default="{row}">{{row.new_position||"-"}}</template></el-table-column>
      <el-table-column prop="reason" label="原因" min-width="150" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{row}"><el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button><el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button></template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[10,20,50]" :total="total" layout="total,sizes,prev,pager,next" style="margin-top:16px" @change="fetchData" />
    <el-dialog v-model="showDialog" :title="isEditing?'编辑记录':'新增记录'" width="600px">
      <el-form :model="form" label-width="100px" label-position="top" style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px">
        <el-form-item label="员工" v-if="!isEditing" required><el-select v-model="form.employee_id" filterable style="width:100%"><el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" /></el-select></el-form-item>
        <el-form-item label="变动日期" required><el-date-picker v-model="form.change_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="变动类型" required><el-select v-model="form.change_type" style="width:100%"><el-option label="入职" value="hire" /><el-option label="晋升" value="promotion" /><el-option label="调岗" value="transfer" /><el-option label="离职" value="resignation" /></el-select></el-form-item>
        <el-form-item label="原因"><el-input v-model="form.reason" /></el-form-item>
        <el-form-item label="原部门"><el-input v-model="form.previous_department" /></el-form-item>
        <el-form-item label="新部门"><el-input v-model="form.new_department" /></el-form-item>
        <el-form-item label="原职位"><el-input v-model="form.previous_position" /></el-form-item>
        <el-form-item label="新职位"><el-input v-model="form.new_position" /></el-form-item>
        <el-form-item label="备注" style="grid-column:1/3"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from "vue"
import { getEmploymentHistories, createEmploymentHistory, updateEmploymentHistory, deleteEmploymentHistory, type EmploymentHistoryItem } from "@/api/employmentHistories"
import { getAttendanceEmployees, type EmployeeOption } from "@/api/attendance"
import { ElMessage, ElMessageBox } from "element-plus"

const list=ref<EmploymentHistoryItem[]>([]); const employees=ref<EmployeeOption[]>([]); const loading=ref(false)
const page=ref(1); const pageSize=ref(20); const total=ref(0); const fEmp=ref(""); const fType=ref("")
const showDialog=ref(false); const isEditing=ref(false); const saving=ref(false); const editId=ref("")
const initForm={employee_id:"",change_date:"",change_type:"hire",previous_department:"",new_department:"",previous_position:"",new_position:"",reason:"",remark:""}
const form=ref<any>({...initForm})
const typeLabel=(s:string)=>({hire:"入职",promotion:"晋升",transfer:"调岗",resignation:"离职"})[s]||s
const typeColor=(s:string)=>({hire:"success",promotion:"warning",transfer:"primary",resignation:"danger"})[s]||"info"

async function fetchData(){loading.value=true;try{const p:any={page:page.value,page_size:pageSize.value};if(fEmp.value)p.employee_id=fEmp.value;if(fType.value)p.change_type=fType.value;const r=await getEmploymentHistories(p);list.value=r?.items||[];total.value=r?.total||0}finally{loading.value=false}}
async function loadEmps(){employees.value=(await getAttendanceEmployees())||[]}
function openCreate(){isEditing.value=false;editId.value="";form.value={...initForm};showDialog.value=true}
function openEdit(r:EmploymentHistoryItem){isEditing.value=true;editId.value=r.id;form.value={...r};showDialog.value=true}
async function handleSave(){saving.value=true;try{if(isEditing.value){await updateEmploymentHistory(editId.value,form.value);ElMessage.success("已更新")}else{await createEmploymentHistory(form.value);ElMessage.success("已创建")}showDialog.value=false;await fetchData()}finally{saving.value=false}}
async function handleDelete(r:EmploymentHistoryItem){await ElMessageBox.confirm("确定删除此履历记录？","提示",{type:"warning"});await deleteEmploymentHistory(r.id);ElMessage.success("已删除");await fetchData()}
onMounted(()=>{fetchData();loadEmps()})
</script>
