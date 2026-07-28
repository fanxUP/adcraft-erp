import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import * as ElementPlusIcons from '@element-plus/icons-vue'
import { resolve } from 'path'
import { writeFileSync } from 'fs'

const elementPlusIconNames = new Set(Object.keys(ElementPlusIcons))

function elementPlusIconResolver(name: string) {
  if (elementPlusIconNames.has(name)) {
    return { name, from: '@element-plus/icons-vue' }
  }
}

function versionPlugin(): import('vite').Plugin {
  return {
    name: 'version-plugin',
    closeBundle() {
      const ts = Date.now()
      const hash = ts.toString(36)
      const content = JSON.stringify({ version: hash, builtAt: new Date().toISOString() }, null, 2)
      const outDir = resolve(__dirname, 'dist')
      writeFileSync(resolve(outDir, 'version.json'), content, 'utf-8')
      console.log(`[version-plugin] version.json written: ${hash}`)
    },
  }
}

export default defineConfig(({ mode }) => ({
  plugins: [
    vue(),
    Components({
      dts: false,
      resolvers: [
        ElementPlusResolver({ importStyle: 'css' }),
        elementPlusIconResolver,
      ],
    }),
    ...(mode === 'test' ? [] : [versionPlugin()]),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (/[\\/]node_modules[\\/](echarts|zrender|vue-echarts)[\\/]/.test(id)) {
            return 'charts'
          }
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
}))
