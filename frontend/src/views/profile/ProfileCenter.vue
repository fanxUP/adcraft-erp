<template>
  <div class="page">
    <div class="page-header"><h2>个人中心</h2></div>

    <el-card class="info-card" shadow="never">
      <template #header>账号信息</template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">{{ authStore.user?.username }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ authStore.user?.real_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ roleLabel }}</el-descriptions-item>
        <el-descriptions-item label="电话">{{ authStore.user?.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ authStore.user?.email || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card class="pwd-card" shadow="never">
      <template #header>修改密码</template>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" style="max-width: 420px">
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="form.old_password" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
        <el-form-item>
          <el-button :loading="submitting" @click="handleSubmit" type="primary">保存</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { changePassword } from '@/api/auth'
import { getErrorMessage } from '@/utils/error'

const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const rules: FormRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.new_password) callback(new Error('两次输入的新密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

const roleLabel = computed(() => {
  const roles = authStore.user?.roles || []
  const map: Record<string, string> = {
    admin: '管理员',
    sales: '销售',
    designer: '设计师',
    production: '制作',
    installer: '安装',
    finance: '财务',
  }
  return roles.map(r => map[r] || r).join('、') || '-'
})

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await changePassword({ old_password: form.old_password, new_password: form.new_password })
    ElMessage.success('密码修改成功')
    form.old_password = ''
    form.new_password = ''
    form.confirm_password = ''
    formRef.value?.clearValidate()
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error))
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.info-card {
  margin-bottom: 16px;
}
.pwd-card {
  max-width: 560px;
}
</style>
