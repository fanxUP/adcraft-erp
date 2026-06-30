<template>
  <div class="login-container">
    <div class="login-card">
      <h1 class="login-title">AdCraft ERP</h1>
      <p class="login-subtitle">广告制作安装工程管理系统</p>
      <el-form ref="formRef" :model="form" :rules="rules" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock" size="large" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="danger" size="large" :loading="loading" @click="handleLogin" style="width: 100%">
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'


const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    router.push('/')
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  width: 100%;
  max-width: 400px;
}

.login-card {
  background: var(--ad-card);
  padding: 40px;
  border-radius: 8px;
  border: 1px solid var(--ad-border);
}

.login-title {
  text-align: center;
  color: #e63946;
  font-size: 28px;
  margin: 0 0 8px;
}

.login-subtitle {
  text-align: center;
  color: var(--ad-text-secondary);
  margin: 0 0 32px;
  font-size: 14px;
}
</style>
