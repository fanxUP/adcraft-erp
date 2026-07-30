<template>
  <div class="page">
    <div class="page-header"><h2>请假审批</h2>
      <div style="display:flex;gap:8px;align-items:center">
        <el-select v-model="fEmp" placeholder="员工" clearable filterable style="width:200px" @change="fetchData">
          <el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" />
        </el-select>
        <el-select v-model="fStatus" placeholder="状态" clearable style="width:110px" @change="fetchData">
          <el-option label="待审批" value="pending" /><el-option label="已通过" value="approved" /><el-option label="已驳回" value="rejected" />
        </el-select>
        <el-select v-model="fType" placeholder="请假类型" clearable style="width:120px" @change="fetchData">
          <el-option label="年假" value="annual" /><el-option label="病假" value="sick" /><el-option label="事假" value="personal" /><el-option label="产假" value="maternity" /><el-option label="其他" value="other" />
        </el-select>
        <el-button type="danger" @click="openCreate">新建申请</el-button>
      </div>
    </div>
    <el-table :data="list" v-loading="loading" stripe style="width:100%">
      <el-table-column label="员工" width="150"><template #default="{row}">{{row.employee_name||row.employee_id}}</template></el-table-column>
      <el-table-column label="请假类型" width="90"><template #default="{row}"><el-tag size="small">{{typeLabel(row.leave_type)}}</el-tag></template></el-table-column>
      <el-table-column prop="start_date" label="开始日期" width="110" />
      <el-table-column prop="end_date" label="结束日期" width="110" />
      <el-table-column prop="duration_days" label="天数" width="60" />
      <el-table-column prop="reason" label="事由" min-width="160" show-overflow-tooltip />
      <el-table-column label="状态" width="90"><template #default="{row}"><el-tag :type="statusColor(row.status)" size="small">{{statusLabel(row.status)}}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{row}">
          <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.status==='pending'" text type="success" size="small" @click="handleApprove(row)">通过</el-button>
          <el-button v-if="row.status==='pending'" text type="warning" size="small" @click="handleReject(row)">驳回</el-button>
          <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[10,20,50]" :total="total" layout="total,sizes,prev,pager,next" style="margin-top:16px" @change="fetchData" />
    <el-dialog v-model="showDialog" :title="isEditing?'编辑申请':'新建请假申请'" width="560px">
      <el-form :model="form" label-width="100px" label-position="top" style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px">
        <el-form-item label="员工" v-if="!isEditing" required><el-select v-model="form.employee_id" filterable style="width:100%"><el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" /></el-select></el-form-item>
        <el-form-item label="请假类型" required><el-select v-model="form.leave_type" style="width:100%"><el-option label="年假" value="annual" /><el-option label="病假" value="sick" /><el-option label="事假" value="personal" /><el-option label="产假" value="maternity" /><el-option label="其他" value="other" /></el-select></el-form-item>
        <el-form-item label="开始日期" required><el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" @change="calcDays" /></el-form-item>
        <el-form-item label="结束日期" required><el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" @change="calcDays" /></el-form-item>
        <el-form-item label="天数" required><el-input-number v-model="form.duration_days" :min="0.5" :step="0.5" style="width:100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
        <el-form-item label="事由" style="grid-column:1/3" required><el-input v-model="form.reason" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from "vue"
import { getLeaveRequests, createLeaveRequest, updateLeaveRequest, approveLeaveRequest, deleteLeaveRequest, type LeaveRequestItem } from "@/api/leaves"
import { getAttendanceEmployees, type EmployeeOption } from "@/api/attendance"
import { ElMessage, ElMessageBox } from "element-plus"

const list=ref<LeaveRequestItem[]>([]); const employees=ref<EmployeeOption[]>([]); const loading=ref(false)
const page=ref(1); const pageSize=ref(20); const total=ref(0); const fEmp=ref(""); const fStatus=ref(""); const fType=ref("")
const showDialog=ref(false); const isEditing=ref(false); const saving=ref(false); const editId=ref("")
const initForm={employee_id:"",leave_type:"annual",start_date:"",end_date:"",duration_days:1,reason:"",remark:""}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const form=ref<any>({...initForm})
const typeLabel=(s:string)=>({annual:"年假",sick:"病假",personal:"事假",maternity:"产假",other:"其他"})[s]||s
const statusLabel=(s:string)=>({pending:"待审批",approved:"已通过",rejected:"已驳回",cancelled:"已取消"})[s]||s
const statusColor=(s:string)=>({pending:"info",approved:"success",rejected:"danger",cancelled:"info"})[s]||"info"
function calcDays(){if(form.value.start_date&&form.value.end_date){const s=new Date(form.value.start_date);const e=new Date(form.value.end_date);const d=Math.ceil((e.getTime()-s.getTime())/(86400000))+1;form.value.duration_days=Math.max(0.5,d)}}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function fetchData(){loading.value=true;try{const p:any={page:page.value,page_size:pageSize.value};if(fEmp.value)p.employee_id=fEmp.value;if(fStatus.value)p.status=fStatus.value;if(fType.value)p.leave_type=fType.value;const r=await getLeaveRequests(p);list.value=r?.items||[];total.value=r?.total||0}finally{loading.value=false}}
async function loadEmps(){employees.value=(await getAttendanceEmployees())||[]}
function openCreate(){isEditing.value=false;editId.value="";form.value={...initForm};showDialog.value=true}
function openEdit(r:LeaveRequestItem){isEditing.value=true;editId.value=r.id;form.value={...r};showDialog.value=true}
async function handleSave(){saving.value=true;try{if(isEditing.value){await updateLeaveRequest(editId.value,form.value);ElMessage.success("已更新")}else{await createLeaveRequest(form.value);ElMessage.success("已创建")}showDialog.value=false;await fetchData()}finally{saving.value=false}}
async function handleApprove(r:LeaveRequestItem){try{await ElMessageBox.confirm("确定通过该请假申请？","审批确认",{type:"info"});await approveLeaveRequest(r.id,{status:"approved"});ElMessage.success("已通过");await fetchData()}catch(e:unknown){const m=(e as {message?:string})?.message;if(m)ElMessage.error(m)}}
async function handleReject(r:LeaveRequestItem){try{await ElMessageBox.confirm("确定驳回该请假申请？","审批确认",{type:"warning"});await approveLeaveRequest(r.id,{status:"rejected"});ElMessage.success("已驳回");await fetchData()}catch(e:unknown){const m=(e as {message?:string})?.message;if(m)ElMessage.error(m)}}
async function handleDelete(r:LeaveRequestItem){await ElMessageBox.confirm("确定删除此请假申请？","提示",{type:"warning"});await deleteLeaveRequest(r.id);ElMessage.success("已删除");await fetchData()}
onMounted(()=>{fetchData();loadEmps()})
</script>
