<template>
  <div class="page">
    <div class="page-header"><h2>部门管理</h2>
      <el-button type="danger" @click="openCreate">新建部门</el-button>
    </div>
    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="code" label="编码" width="120" />
      <el-table-column prop="name" label="名称" width="120" />
      <el-table-column label="启用" width="80"><template #default="{row}"><el-tag :type="row.is_active?'success':'info'" size="small">{{ row.is_active?'是':'否' }}</el-tag></template></el-table-column>
      <el-table-column prop="sort_order" label="排序" width="70" />
      <el-table-column prop="description" label="描述" min-width="180" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{row}"><el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button><el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button></template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="showDialog" :title="isEditing?'编辑部门':'新建部门'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="编码" required><el-input v-model="form.code" :disabled="isEditing" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort_order" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from "vue"
import { getDepartments, createDepartment, updateDepartment, deleteDepartment, type DepartmentItem } from "@/api/departments"
import { ElMessage, ElMessageBox } from "element-plus"

const list=ref<DepartmentItem[]>([]); const loading=ref(false)
const showDialog=ref(false); const isEditing=ref(false); const saving=ref(false); const editId=ref("")
const form=ref<Record<string, unknown>>({name:"",code:"",sort_order:0,description:"",is_active:true})

async function fetchData(){loading.value=true;try{list.value=(await getDepartments())||[]}finally{loading.value=false}}
function openCreate(){isEditing.value=false;editId.value="";form.value={name:"",code:"",sort_order:0,description:"",is_active:true};showDialog.value=true}
function openEdit(r:DepartmentItem){isEditing.value=true;editId.value=r.id;form.value={...r};showDialog.value=true}
async function handleSave(){saving.value=true;try{if(isEditing.value){await updateDepartment(editId.value,form.value);ElMessage.success("已更新")}else{await createDepartment(form.value);ElMessage.success("已创建")}showDialog.value=false;await fetchData()}catch(e:unknown){ElMessage.error((e as {message?:string})?.message||"操作失败")}finally{saving.value=false}}
async function handleDelete(r:DepartmentItem){try{await ElMessageBox.confirm("确定删除部门 "+r.name+"？","提示",{type:"warning"});await deleteDepartment(r.id);ElMessage.success("已删除");await fetchData()}catch(e:unknown){const m=(e as {message?:string})?.message;if(m)ElMessage.error(m)}}
onMounted(fetchData)
</script>
