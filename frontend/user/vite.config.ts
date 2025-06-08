import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      // API代理到后端服务器
      '/api': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
        secure: false,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('❌ 代理错误:', err);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('📤 代理请求:', req.method, req.url, '-> http://localhost:5001' + req.url);
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log('📥 代理响应:', proxyRes.statusCode, req.url);
          });
        }
      },
      // WebSocket 代理配置
      '/socket.io': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
        ws: true,
        secure: false,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('❌ WebSocket 代理错误:', err);
          });
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': '/src'
    }
  },
  build: {
    outDir: '../../static/user',  // 构建到后端静态目录
    emptyOutDir: true,
    assetsDir: 'assets'
  },
  base: '/user/'  // 重要：设置基础路径
})