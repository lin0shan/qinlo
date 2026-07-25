/**
 * 响应式布局检测
 *
 * 监听窗口宽度变化，>= 1280px 视为 PC 端，
 * PC 端自动切换 DataTable 表格视图。
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'

const PC_BREAKPOINT = 1280
const width = ref(window.innerWidth)

function onResize() {
  width.value = window.innerWidth
}

export function useLayout() {
  const isPC = computed(() => width.value >= PC_BREAKPOINT)

  onMounted(() => window.addEventListener('resize', onResize))
  onUnmounted(() => window.removeEventListener('resize', onResize))

  return { isPC, width }
}
