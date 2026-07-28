<template>
  <div class="mobile-page">
    <!-- Profile header -->
    <div class="profile-header">
      <div class="avatar">{{ initials }}</div>
      <div class="profile-info">
        <div class="profile-name">{{ authStore.user?.real_name || authStore.user?.username }}</div>
        <div class="profile-role">{{ roleLabel }}</div>
        <div v-if="authStore.user?.phone" class="profile-phone">{{ authStore.user.phone }}</div>
      </div>
    </div>

    <!-- Info cards -->
    <div class="info-section">
      <div class="info-title">账号信息</div>
      <div class="info-card">
        <div class="info-row">
          <span class="info-label">用户名</span>
          <span class="info-value">{{ authStore.user?.username }}</span>
        </div>
        <div class="info-row" v-if="authStore.user?.real_name">
          <span class="info-label">姓名</span>
          <span class="info-value">{{ authStore.user.real_name }}</span>
        </div>
        <div class="info-row" v-if="authStore.user?.phone">
          <span class="info-label">电话</span>
          <a :href="`tel:${authStore.user.phone}`" class="info-value phone-link">{{ authStore.user.phone }}</a>
        </div>
      </div>
    </div>

    <!-- Quick links -->
    <div class="info-section">
      <div class="info-title">快捷入口</div>
      <div class="link-list">
        <div class="link-item" @click="goTo('/mobile/installation')">
          <span class="link-icon">📋</span>
          <span class="link-text">安装任务</span>
          <span class="link-arrow">›</span>
        </div>
        <div class="link-item" @click="goTo('/')">
          <span class="link-icon">🖥️</span>
          <span class="link-text">桌面端完整版</span>
          <span class="link-arrow">›</span>
        </div>
      </div>
    </div>

    <!-- Logout button -->
    <div class="logout-section">
      <button class="logout-btn" @click="handleLogout">退出登录</button>
    </div>

    <!-- App info -->
    <div class="app-info">
      <span>AdCraft ERP v1.0</span>
      <span>广告制作安装工程管理系统</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

const initials = computed(() => {
  const name = authStore.user?.real_name || authStore.user?.username || 'U'
  return name.charAt(0).toUpperCase()
})

const roleLabel = computed(() => {
  const roles = authStore.user?.roles || []
  if (roles.includes('admin')) return '管理员'
  if (roles.includes('installer')) return '安装师傅'
  if (roles.includes('production')) return '制作人员'
  if (roles.includes('designer')) return '设计师'
  if (roles.includes('sales')) return '销售'
  if (roles.includes('finance')) return '财务'
  return ''
})

function goTo(path: string) {
  router.push(path)
}

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定退出登录？', '退出', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    authStore.logout()
  } catch {
    // cancelled
  }
}
</script>

<style scoped>
.mobile-page {
  max-width: 480px;
  margin: 0 auto;
  min-height: calc(100vh - 64px);
  padding: 0 0 24px;
  background: #0f0f1a;
  color: var(--ad-text, #e0e0e0);
}

/* Profile header */
.profile-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px 16px;
  background: linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%);
}
.avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--ad-red, #e63946);
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.profile-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.profile-name {
  font-size: 20px;
  font-weight: 700;
}
.profile-role {
  font-size: 13px;
  color: #888;
}
.profile-phone {
  font-size: 13px;
  color: #4fc3f7;
  margin-top: 2px;
}

/* Info sections */
.info-section {
  padding: 8px 16px;
}
.info-title {
  font-size: 14px;
  font-weight: 600;
  color: #888;
  margin-bottom: 8px;
  padding-left: 4px;
}
.info-card {
  background: #1e1e30;
  border: 1px solid #2a2a3e;
  border-radius: 10px;
  padding: 4px 12px;
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #2a2a3e;
}
.info-row:last-child { border-bottom: none; }
.info-label {
  font-size: 14px;
  color: #888;
}
.info-value {
  font-size: 14px;
  text-align: right;
}
.phone-link {
  color: #4fc3f7;
  text-decoration: none;
}

/* Link list */
.link-list {
  background: #1e1e30;
  border: 1px solid #2a2a3e;
  border-radius: 10px;
  overflow: hidden;
}
.link-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 12px;
  border-bottom: 1px solid #2a2a3e;
  cursor: pointer;
  transition: background 0.15s;
  -webkit-tap-highlight-color: transparent;
}
.link-item:last-child { border-bottom: none; }
.link-item:active { background: #2a2a3e; }
.link-icon { font-size: 20px; }
.link-text { flex: 1; font-size: 14px; }
.link-arrow { font-size: 18px; color: #555; }

/* Logout */
.logout-section {
  padding: 24px 16px 8px;
}
.logout-btn {
  width: 100%;
  padding: 14px;
  border-radius: 10px;
  border: 1px solid #e63946;
  background: transparent;
  color: #e63946;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  -webkit-tap-highlight-color: transparent;
}
.logout-btn:active {
  background: #e63946;
  color: #fff;
}

/* App info */
.app-info {
  text-align: center;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #444;
}
</style>
