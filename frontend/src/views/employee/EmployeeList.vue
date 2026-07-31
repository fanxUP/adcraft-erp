<template>
  <div class="page">
    <div class="page-header"><h2>员工管理</h2>
      <div style="display:flex;gap:8px;align-items:center">
        <el-select v-model="filterDept" placeholder="部门筛选" clearable style="width:130px" @change="fetchData">
          <el-option v-for="d in DEPTS" :key="d.value" :label="d.label" :value="d.value" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width:110px" @change="fetchData">
          <el-option label="在职" value="active" /><el-option label="离职" value="resigned" /><el-option label="停职" value="suspended" />
        </el-select>
        <el-input v-model="keyword" placeholder="搜索姓名/工号/手机号" clearable style="width:240px" @clear="fetchData" @keyup.enter="fetchData" />
        <el-button type="danger" @click="openCreate">新建员工</el-button>
      </div>
    </div>
    <el-table :data="list" v-loading="loading" stripe style="width:100%">
      <el-table-column prop="employee_no" label="工号" width="120" />
      <el-table-column prop="name" label="姓名" width="240" />
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column label="性别" width="60"><template #default="{row}">{{ {male:"男",female:"女"} [row.gender] || row.gender || "-" }}</template></el-table-column>
      <el-table-column label="部门" width="120"><template #default="{row}">{{ deptLabel(row.department) }}</template></el-table-column>
      <el-table-column prop="position" label="职位" width="120" />
      <el-table-column label="聘用类型" width="100"><template #default="{row}">{{ typeLabel(row.employment_type) }}</template></el-table-column>
      <el-table-column label="学历" width="70"><template #default="{row}">{{ row.education || "-" }}</template></el-table-column>
      <el-table-column prop="hire_date" label="入职日期" width="120" />
      <el-table-column label="状态" width="100"><template #default="{row}"><el-tag :type="statusColor(row.employment_status)" size="small">{{ statusLabel(row.employment_status) }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{row}"><el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button><el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button></template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[10,20,50]" :total="total" layout="total,sizes,prev,pager,next" style="margin-top:16px" @change="fetchData" />
    <el-dialog v-model="showDialog" :title="isEditing?'编辑员工':'新建员工'" width="820px" top="5vh">
      <el-form :model="form" label-width="90px" label-position="top" style="display:grid;grid-template-columns:1fr 1fr;gap:0 20px">
        <el-form-item label="姓名" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="性别"><el-select v-model="form.gender" clearable style="width:100%"><el-option label="男" value="male" /><el-option label="女" value="female" /></el-select></el-form-item>
        <el-form-item label="出生日期"><el-date-picker v-model="form.birth_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="部门"><el-select v-model="form.department" clearable style="width:100%"><el-option v-for="d in DEPTS" :key="d.value" :label="d.label" :value="d.value" /></el-select></el-form-item>
        <el-form-item label="职位"><el-input v-model="form.position" /></el-form-item>
        <el-form-item label="聘用类型"><el-select v-model="form.employment_type" clearable style="width:100%"><el-option label="全职" value="full_time" /><el-option label="兼职" value="part_time" /><el-option label="合同" value="contract" /><el-option label="实习" value="intern" /></el-select></el-form-item>
        <el-form-item label="学历"><el-select v-model="form.education" clearable style="width:100%"><el-option label="初中" value="middle_school" /><el-option label="高中" value="high_school" /><el-option label="中专" value="vocational" /><el-option label="大专" value="college" /><el-option label="本科" value="bachelor" /><el-option label="硕士" value="master" /><el-option label="博士" value="phd" /></el-select></el-form-item>
        <el-form-item label="身份证号"><el-input v-model="form.id_card" /></el-form-item>
        <el-form-item label="入职日期"><el-date-picker v-model="form.hire_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="离职日期"><el-date-picker v-model="form.resignation_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="在职状态"><el-select v-model="form.employment_status" style="width:100%"><el-option label="在职" value="active" /><el-option label="离职" value="resigned" /><el-option label="停职" value="suspended" /></el-select></el-form-item>
        <el-form-item label="紧急联系人"><el-input v-model="form.emergency_contact" /></el-form-item>
        <el-form-item label="紧急联系电话"><el-input v-model="form.emergency_phone" /></el-form-item>
        <el-form-item label="技能标签"><el-select v-model="form.skills" multiple filterable allow-create default-first-option style="width:100%" placeholder="输入技能后回车添加"><el-option v-for="s in form.skills || []" :key="s" :label="s" :value="s" /></el-select></el-form-item>
        <el-form-item label="基本工资"><el-input-number v-model="form.base_salary" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="开户行"><el-input v-model="form.bank_name" /></el-form-item>
        <el-form-item label="银行账号"><el-input v-model="form.bank_account" /></el-form-item>
        <el-form-item label="家庭地址" style="grid-column:1/3"><el-input v-model="form.address" /></el-form-item>
        <el-form-item label="备注" style="grid-column:1/3"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template v-if="isEditing">
        <el-divider />
        <div style="margin-bottom:12px;display:flex;align-items:center;justify-content:space-between">
          <strong>附件</strong>
          <el-upload :http-request="handleUploadAttachment" :show-file-list="false" multiple>
            <el-button type="danger" size="small">上传附件</el-button>
          </el-upload>
        </div>
        <div v-if="attachments.length" style="display:flex;flex-wrap:wrap;gap:8px">
          <div v-for="att in attachments" :key="att.id" style="display:flex;align-items:center;gap:6px;padding:6px 10px;border:1px solid #e4e7ed;border-radius:4px;font-size:13px">
            <a :href="'/uploads/'+att.file_path" target="_blank" style="color:#409eff;text-decoration:none">{{ att.filename }}</a>
            <el-button text type="danger" size="small" @click="handleDeleteAttachment(att.id)">删除</el-button>
          </div>
        </div>
        <div v-else style="color:#999;font-size:13px">暂无附件</div>
      </template>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from "vue"
import { getEmployees, createEmployee, updateEmployee, deleteEmployee, getEmployeeAttachments, uploadEmployeeAttachment, deleteEmployeeAttachment, type EmployeeResponse } from "@/api/employees"
import type { AttachmentResponse } from "@/types/api"
import { ElMessage, ElMessageBox } from "element-plus"
import type { UploadRequestOptions } from "element-plus"

const DEPTS = [{value:"design",label:"设计部"},{value:"production",label:"生产部"},{value:"installation",label:"安装部"},{value:"sales",label:"销售部"},{value:"finance",label:"财务部"},{value:"admin",label:"行政部"}]
const list=ref<EmployeeResponse[]>([]); const loading=ref(false); const page=ref(1); const pageSize=ref(20); const total=ref(0); const keyword=ref(""); const filterDept=ref(""); const filterStatus=ref("")
const showDialog=ref(false); const isEditing=ref(false); const saving=ref(false); const editId=ref("")
const attachments=ref<AttachmentResponse[]>([])
const initForm={name:"",phone:"",gender:"",birth_date:"",department:"",position:"",employment_type:"",education:"",id_card:"",hire_date:"",resignation_date:"",employment_status:"active",emergency_contact:"",emergency_phone:"",skills:[],base_salary:null,bank_name:"",bank_account:"",address:"",remark:""}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const form=ref<any>({...initForm})
const deptLabel=(v:string)=>DEPTS.find(d=>d.value===v)?.label||v
const typeLabel=(v:string)=>({full_time:"全职",part_time:"兼职",contract:"合同",intern:"实习"})[v]||v||"-"
const statusLabel=(s:string)=>({active:"在职",resigned:"离职",suspended:"停职"})[s]||s
const statusColor=(s:string)=>({active:"success",resigned:"info",suspended:"warning"})[s]||"info"

async function fetchData(){loading.value=true;try{const r=await getEmployees({page:page.value,page_size:pageSize.value,keyword:keyword.value||undefined,department:filterDept.value||undefined,employment_status:filterStatus.value||undefined});list.value=r?.items||[];total.value=r?.total||0}finally{loading.value=false}}
async function loadAttachments(){attachments.value=(await getEmployeeAttachments(editId.value))||[]}
function openCreate(){isEditing.value=false;editId.value="";attachments.value=[];form.value={...initForm};showDialog.value=true}
function openEdit(r:EmployeeResponse){isEditing.value=true;editId.value=r.id;form.value={...r,skills:r.skills||[]};showDialog.value=true;loadAttachments()}
async function handleSave(){saving.value=true;try{if(isEditing.value){await updateEmployee(editId.value,form.value);ElMessage.success("已更新")}else{await createEmployee(form.value);ElMessage.success("已创建")}showDialog.value=false;await fetchData()}finally{saving.value=false}}
async function handleDelete(r:EmployeeResponse){await ElMessageBox.confirm("确定删除？","提示",{type:"warning"});await deleteEmployee(r.id);ElMessage.success("已删除");await fetchData()}
async function handleUploadAttachment(options: UploadRequestOptions){try{await uploadEmployeeAttachment(editId.value,options.file);ElMessage.success("上传成功");await loadAttachments()}catch{ElMessage.error("上传失败")}}
async function handleDeleteAttachment(aid:string){await ElMessageBox.confirm("确定删除此附件？","提示",{type:"warning"});await deleteEmployeeAttachment(aid);ElMessage.success("已删除");await loadAttachments()}
onMounted(fetchData)
</script>
