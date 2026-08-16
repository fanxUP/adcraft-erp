<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-brand">
        <span class="logo-mark">A</span>
      </div>
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
          <el-button type="primary" size="large" :loading="loading" @click="handleLogin" class="login-btn">
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
  padding: 20px;
}

.login-card {
  background: var(--ad-card);
  padding: 40px 40px 32px;
  border-radius: 12px;
  border: 1px solid var(--ad-border);
  box-shadow: 0 8px 32px rgba(15, 23, 42, 0.08);
}

.login-brand {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.logo-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #fff;
  font-size: 28px;
  font-weight: 800;
}

.login-title {
  text-align: center;
  color: var(--ad-text);
  font-size: 24px;
  margin: 0 0 6px;
  font-weight: 700;
}

.login-subtitle {
  text-align: center;
  color: var(--ad-text-secondary);
  margin: 0 0 28px;
  font-size: 14px;
}

.login-btn {
  width: 100%;
}

/* Mobile responsive */
@media (max-width: 480px) {
  .login-container {
    max-width: 100%;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    box-sizing: border-box;
  }
  .login-card {
    width: 100%;
    padding: 32px 24px;
  }
  .login-title {
    font-size: 22px;
  }
  .login-subtitle {
    font-size: 13px;
  }
}
</style>
