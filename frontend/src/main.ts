/// <reference types="element-plus/global" />
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import './styles/print.scss'
import './styles/global.scss'
import './styles/themes.scss'
// MessageBox 通过函数调用创建，不经过模板自动按需加载，需显式引入其布局样式。
import 'element-plus/es/components/message-box/style/css'
import 'element-plus/theme-chalk/el-message-box.css'

const app = createApp(App)

app.use(router)
app.use(createPinia())

app.mount('#app')
