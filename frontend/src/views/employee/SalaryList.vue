<template>
  <div class="page">
    <div class="page-header"><h2>工资管理</h2>
      <div style="display:flex;gap:8px;align-items:center">
        <el-select v-model="fEmp" placeholder="员工" clearable filterable style="width:200px" @change="fetchData">
          <el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" />
        </el-select>
        <el-input v-model="fMonth" placeholder="月份 YYYY-MM" style="width:140px" clearable @change="fetchData" />
        <el-select v-model="fStatus" placeholder="支付状态" clearable style="width:120px" @change="fetchData">
          <el-option label="待核算" value="pending" /><el-option label="已核算" value="calculated" /><el-option label="已发放" value="paid" />
        </el-select>
        <el-button type="danger" @click="openCreate">录入工资</el-button>
      </div>
    </div>
    <el-table :data="list" v-loading="loading" stripe style="width:100%">
      <el-table-column prop="month" label="月份" width="100" />
      <el-table-column label="员工" width="150"><template #default="{row}">{{row.employee_name||row.employee_id}}</template></el-table-column>
      <el-table-column prop="base_salary" label="基本工资" width="110" align="right"><template #default="{row}">{{fmt(row.base_salary)}}</template></el-table-column>
      <el-table-column prop="overtime_pay" label="加班费" width="100" align="right"><template #default="{row}">{{fmt(row.overtime_pay)}}</template></el-table-column>
      <el-table-column prop="bonus" label="奖金" width="90" align="right"><template #default="{row}">{{fmt(row.bonus)}}</template></el-table-column>
      <el-table-column prop="commission" label="提成" width="90" align="right"><template #default="{row}">{{fmt(row.commission)}}</template></el-table-column>
      <el-table-column prop="subsidy" label="补贴" width="90" align="right"><template #default="{row}">{{fmt(row.subsidy)}}</template></el-table-column>
      <el-table-column prop="deduction" label="扣款" width="90" align="right"><template #default="{row}">{{fmt(row.deduction)}}</template></el-table-column>
      <el-table-column prop="net_salary" label="实发" width="110" align="right"><template #default="{row}"><strong>{{fmt(row.net_salary)}}</strong></template></el-table-column>
      <el-table-column label="状态" width="90"><template #default="{row}"><el-tag :type="payStatusColor(row.payment_status)" size="small">{{payStatusLabel(row.payment_status)}}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{row}"><el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button><el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button></template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[10,20,50]" :total="total" layout="total,sizes,prev,pager,next" style="margin-top:16px" @change="fetchData" />
    <el-dialog v-model="showDialog" :title="isEditing?'编辑工资':'录入工资'" width="640px">
      <el-form :model="form" label-width="100px" label-position="top" style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px">
        <el-form-item label="员工" v-if="!isEditing" required><el-select v-model="form.employee_id" filterable style="width:100%"><el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" /></el-select></el-form-item>
        <el-form-item label="月份" required><el-input v-model="form.month" placeholder="YYYY-MM" style="width:100%" /></el-form-item>
        <el-form-item label="基本工资"><el-input-number v-model="form.base_salary" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="加班费"><el-input-number v-model="form.overtime_pay" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="奖金"><el-input-number v-model="form.bonus" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="提成"><el-input-number v-model="form.commission" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="补贴"><el-input-number v-model="form.subsidy" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="扣款"><el-input-number v-model="form.deduction" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="实发工资" required><el-input-number v-model="form.net_salary" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="支付状态"><el-select v-model="form.payment_status" style="width:100%"><el-option label="待核算" value="pending" /><el-option label="已核算" value="calculated" /><el-option label="已发放" value="paid" /></el-select></el-form-item>
        <el-form-item label="备注" style="grid-column:1/3"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from "vue"
import { getSalaries, createSalary, updateSalary, deleteSalary, type SalaryRecordItem } from "@/api/salaries"
import { getAttendanceEmployees, type EmployeeOption } from "@/api/attendance"
import { ElMessage, ElMessageBox } from "element-plus"

const list=ref<SalaryRecordItem[]>([]); const employees=ref<EmployeeOption[]>([]); const loading=ref(false)
const page=ref(1); const pageSize=ref(20); const total=ref(0)
const fEmp=ref(""); const fMonth=ref(""); const fStatus=ref("")
const showDialog=ref(false); const isEditing=ref(false); const saving=ref(false); const editId=ref("")
const initForm={employee_id:"",month:"",base_salary:0,overtime_pay:null,bonus:null,commission:null,subsidy:null,deduction:null,net_salary:0,payment_status:"pending",remark:""}
const form=ref<any>({...initForm})
const fmt=(v:any)=>v!=null?Number(v).toFixed(2):"-"
const payStatusLabel=(s:string)=>({pending:"待核算",calculated:"已核算",paid:"已发放"})[s]||s
const payStatusColor=(s:string)=>({pending:"info",calculated:"warning",paid:"success"})[s]||"info"

async function fetchData(){loading.value=true;try{const p:any={page:page.value,page_size:pageSize.value};if(fEmp.value)p.employee_id=fEmp.value;if(fMonth.value)p.month=fMonth.value;if(fStatus.value)p.payment_status=fStatus.value;const r=await getSalaries(p);list.value=r?.items||[];total.value=r?.total||0}finally{loading.value=false}}
async function loadEmps(){employees.value=(await getAttendanceEmployees())||[]}
function openCreate(){isEditing.value=false;editId.value="";form.value={...initForm};showDialog.value=true}
function openEdit(r:SalaryRecordItem){isEditing.value=true;editId.value=r.id;form.value={...r};showDialog.value=true}
async function handleSave(){saving.value=true;try{if(isEditing.value){await updateSalary(editId.value,form.value);ElMessage.success("已更新")}else{await createSalary(form.value);ElMessage.success("已创建")}showDialog.value=false;await fetchData()}finally{saving.value=false}}
async function handleDelete(r:SalaryRecordItem){await ElMessageBox.confirm("确定删除此工资记录？","提示",{type:"warning"});await deleteSalary(r.id);ElMessage.success("已删除");await fetchData()}
onMounted(()=>{fetchData();loadEmps()})
</script>
