import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// dev 用 '/'(开发期访问 http://localhost:5173/ 干净),
// build 用 '/static/'(生产 FastAPI 把 SPA 挂在 /static/ 路径)
export default defineConfig(({ command }) => ({
  plugins: [vue()],
  root: '.',
  base: command === 'build' ? '/static/' : '/',
  build: {
    outDir: '../static',
    emptyOutDir: true,
    assetsDir: 'assets',
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
}))
