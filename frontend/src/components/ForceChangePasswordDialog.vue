<template>
  <el-dialog
    v-model="visible"
    title="请先修改初始密码"
    width="440px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    :append-to-body="true"
    align-center
  >
    <div class="dialog-tip">
      出于安全考虑，首次登录或密码被重置后，需要先设置一个新密码才能继续使用系统。
    </div>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" @submit.prevent>
      <el-form-item label="原密码" prop="old_password">
        <el-input v-model="form.old_password" type="password" show-password placeholder="请输入当前密码" />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="form.new_password" type="password" show-password placeholder="至少 6 位" />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirm_password">
        <el-input v-model="form.confirm_password" type="password" show-password placeholder="再次输入新密码" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button type="primary" :loading="submitting" style="width: 100%" @click="handleSubmit">
        确认修改
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { changePassword } from '@/api/auth'

const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)

// 用户处于强制改密状态时自动弹出，且不可关闭
const visible = computed(() => authStore.isLoggedIn && authStore.user?.must_change_password === true)

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const rules: FormRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
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

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await changePassword({ old_password: form.old_password, new_password: form.new_password })
    ElMessage.success('密码修改成功，请使用新密码登录')
    authStore.clearMustChangePassword()
    form.old_password = ''
    form.new_password = ''
    form.confirm_password = ''
    formRef.value?.clearValidate()
  } catch {
    // 错误提示已由 axios 拦截器统一弹出（如“原密码错误”/“网络错误”），这里不再重复提示
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.dialog-tip {
  margin-bottom: 16px;
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning-dark-2);
  font-size: 13px;
  line-height: 1.6;
}
</style>
