import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import Vant from 'vant'
import 'vant/lib/index.css'
import './style.css'
import App from './App.vue'
import routes from './router'

const app = createApp(App)
const pinia = createPinia()
const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

app.use(pinia)
app.use(router)
app.use(Vant)
app.mount('#app')
