<template>
  <div class="home-view">
    <h2>首页驾驶舱</h2>
    <el-row :gutter="20">
      <el-col :span="6" v-for="card in cards" :key="card.label">
        <el-card class="stat-card">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value">{{ card.value }}</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
const cards = [
  { label: '今日订单金额', value: '¥ 0.00' },
  { label: '今日收款金额', value: '¥ 0.00' },
  { label: '本月订单金额', value: '¥ 0.00' },
  { label: '本月未收款', value: '¥ 0.00' },
  { label: '待制作', value: '0' },
  { label: '待安装', value: '0' },
  { label: '逾期订单', value: '0' },
  { label: '逾期欠款', value: '¥ 0.00' },
]
</script>

<style scoped>
.home-view h2 {
  margin: 0 0 20px;
  color: var(--ad-text);
}

.stat-card {
  background: var(--ad-card);
  border: 1px solid var(--ad-border);
  color: var(--ad-text);
  margin-bottom: 16px;
}

.stat-label {
  font-size: 13px;
  color: var(--ad-text-secondary);
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #e63946;
  margin-top: 8px;
}
</style>
