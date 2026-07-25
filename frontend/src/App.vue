<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useOffline } from './composables/useOffline'

const router = useRouter()
const route = useRoute()
const { status, pendingCount } = useOffline()

const tabs = [
  { name: 'Inventory', label: '库存', icon: 'home-o' },
  { name: 'Sale', label: '开单', icon: 'scan' },
  { name: 'Products', label: '商品', icon: 'goods-collect-o' },
  { name: 'ImportProducts', label: '导入', icon: 'orders-o' },
  { name: 'Shipments', label: '发货', icon: 'logistics' },
  { name: 'Reports', label: '报表', icon: 'chart-trending-o' },
  { name: 'Coupons', label: '兑换券', icon: 'coupon-o' },
  { name: 'Members', label: '会员', icon: 'friends-o' },
  { name: 'Settings', label: '设置', icon: 'setting-o' },
]

const active = ref(route.name as string)
const isPC = ref(false)

function checkScreen() {
  isPC.value = window.innerWidth >= 1280
}
onMounted(() => {
  checkScreen()
  window.addEventListener('resize', checkScreen)
})
onUnmounted(() => {
  window.removeEventListener('resize', checkScreen)
})

function onTabChange(name: string) {
  active.value = name
  router.push({ name })
}

function onNavClick(name: string) {
  active.value = name
  router.push({ name })
}

// Check if element is visible (not display:none / visibility:hidden / zero size)
function isElementVisible(el: Element): boolean {
  const rect = el.getBoundingClientRect()
  if (rect.width === 0 && rect.height === 0) return false
  const style = window.getComputedStyle(el)
  return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0'
}

// Keyboard shortcuts
function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'F2') {
    e.preventDefault()
    const input = document.querySelector('input[placeholder]') as HTMLInputElement
    if (input) input.focus()
  }
  if (e.key === 'Escape') {
    // Close any open popup (rely on Vant's built-in handling)
  }
  if (e.key === 'Enter') {
    // Skip Enter inside input fields to preserve native behavior (form submit, textarea newline)
    const tag = (e.target as HTMLElement)?.tagName?.toLowerCase()
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return
    if ((e.target as HTMLElement)?.isContentEditable) return

    // Prioritize van-dialog confirm button
    const dialogConfirm = document.querySelector('.van-dialog .van-dialog__confirm')
    if (dialogConfirm && isElementVisible(dialogConfirm)) {
      e.preventDefault()
      ;(dialogConfirm as HTMLElement).click()
      return
    }

    // Handle van-popup confirm button (last visible primary/danger button in visible popups)
    const popups = document.querySelectorAll('.van-overflow-hidden .van-popup, .van-popup--center, .van-popup--bottom')
    for (const popup of popups) {
      if (!isElementVisible(popup)) continue
      const btn = popup.querySelector('.van-button--primary, .van-button--danger') as HTMLElement
      if (btn && isElementVisible(btn)) {
        e.preventDefault()
        btn.click()
        return
      }
    }
  }
}
onMounted(() => document.addEventListener('keydown', onKeyDown))
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))

const statusInfo: Record<string, { text: string; color: string; bg: string }> = {
  online: { text: '在线', color: '#07c160', bg: '#e8f8ee' },
  offline: { text: '离线', color: '#ff976a', bg: '#fff3eb' },
  syncing: { text: '同步中…', color: '#1989fa', bg: '#e8f2ff' },
  sync_failed: { text: '同步失败', color: '#ee0a24', bg: '#fde8ec' },
}
</script>

<template>
  <div class="app-container" :class="{ 'pc-layout': isPC }">
    <!-- 同步状态栏 -->
    <div
      class="sync-bar"
      v-if="status !== 'online'"
      :style="{ color: statusInfo[status]?.color, background: statusInfo[status]?.bg }"
    >
      <span>{{ statusInfo[status]?.text }}</span>
      <span v-if="pendingCount > 0" style="margin-left:8px">{{ pendingCount }} 条待同步</span>
    </div>

    <!-- PC 侧边栏 -->
    <aside v-if="isPC" class="pc-sidebar">
      <div class="sidebar-brand">商业助手</div>
      <nav>
        <div
          v-for="tab in tabs"
          :key="tab.name"
          class="sidebar-item"
          :class="{ active: active === tab.name }"
          @click="onNavClick(tab.name)"
        >
          <van-icon :name="tab.icon" size="18" />
          <span>{{ tab.label }}</span>
        </div>
      </nav>
    </aside>

    <main class="app-main">
      <router-view />
    </main>

    <!-- 移动端 TabBar -->
    <van-tabbar
      v-if="!isPC"
      v-model="active"
      :fixed="true"
      :border="true"
      active-color="#ff6b81"
      @change="onTabChange"
    >
      <van-tabbar-item
        v-for="tab in tabs"
        :key="tab.name"
        :name="tab.name"
        :icon="tab.icon"
      >
        {{ tab.label }}
      </van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  background: #f7f8fa;
}
.app-main {
  padding-bottom: 50px;
}

/* ====== PC Layout ====== */
.pc-layout {
  display: flex;
}
.pc-layout .app-main {
  flex: 1;
  margin-left: 200px;
  padding-bottom: 0;
  min-height: 100vh;
}
.pc-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: 200px;
  height: 100vh;
  background: #1a1a2e;
  color: #eee;
  z-index: 100;
  display: flex;
  flex-direction: column;
}
.sidebar-brand {
  padding: 20px 16px;
  font-size: 18px;
  font-weight: 700;
  color: #ff6b81;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  margin-bottom: 8px;
}
.sidebar-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  font-size: 14px;
  color: rgba(255,255,255,0.65);
  transition: all 0.15s;
  border-left: 3px solid transparent;
}
.sidebar-item:hover {
  color: #fff;
  background: rgba(255,255,255,0.05);
}
.sidebar-item.active {
  color: #ff6b81;
  background: rgba(255,107,129,0.1);
  border-left-color: #ff6b81;
}

/* ====== Sync Bar ====== */
.sync-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 999;
  padding: 4px 16px;
  font-size: 12px;
  text-align: center;
  font-weight: 500;
}
.pc-layout .sync-bar {
  left: 200px;
}
</style>
