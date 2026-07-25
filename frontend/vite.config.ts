import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import fs from 'node:fs'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [
    vue(),
    // PWA 仅在生产构建时启用，开发模式禁用避免 Service Worker 缓存干扰
    ...(mode === 'production'
      ? [
          VitePWA({
            registerType: 'autoUpdate',
            workbox: {
              globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
              runtimeCaching: [
                {
                  urlPattern: /^\/api\/v1\//,
                  handler: 'NetworkFirst',
                  options: {
                    cacheName: 'api-cache',
                    expiration: { maxEntries: 100, maxAgeSeconds: 3600 },
                  },
                },
              ],
            },
            manifest: {
              name: '个人商业助手',
              short_name: '商业助手',
              description: '美妆行业进销存 + 会员管理',
              theme_color: '#ff6b81',
              icons: [
                { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png' },
                { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png' },
              ],
            },
          }),
        ]
      : []),
  ],
  server: {
    // 监听所有网络接口，移动端才能访问
    host: '0.0.0.0',
    // 使用自签名证书，SAN 包含局域网 IP，移动端才能通过 HTTPS 访问摄像头
    https: {
      key: fs.readFileSync('./certs/localhost-key.pem'),
      cert: fs.readFileSync('./certs/localhost.pem'),
    },
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/docs': 'http://127.0.0.1:8000',
      '/uploads': 'http://127.0.0.1:8000',
    },
  },
}))
