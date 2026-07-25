<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { findProductOffline } from '../db/cache'
import { queueOperation } from '../db/sync'
import { useScanner } from '../composables/useScanner'
import { useLayout } from '../composables/useLayout'

const API = '/api/v1'
const { startScan, stopScan, startCamera, stopCamera, playBeep } = useScanner()
const { isPC } = useLayout()

interface PendingItem {
  product_id: number
  product_name: string
  sku_code: string
  barcode: string
  spec: string
  quantity: number
  unit_price: number
}

interface OrderItem {
  id: number
  product_id: number
  product_name: string
  quantity: number
  unit_price: number
}

interface CompletedOrder {
  id: number
  order_number: string
  total_amount: number
  actual_amount: number
  status: string
  member_name: string | null
  items: OrderItem[]
  created_at: string
}

// Order detail popup
const showOrderDetail = ref(false)
const detailOrder = ref<CompletedOrder | null>(null)

function viewOrderDetail(order: CompletedOrder) {
  detailOrder.value = order
  showOrderDetail.value = true
}

// Generate order number (frontend preview only)
/**
 * 生成北京时间的日期字符串 YYYYMMDD（不使用 toISOString，它返回 UTC）
 */
function beijingDateStr(date: Date): string {
  const y = date.getFullYear()
  const m = (date.getMonth() + 1).toString().padStart(2, '0')
  const d = date.getDate().toString().padStart(2, '0')
  return `${y}${m}${d}`
}

function generateOrderNumber(): string {
  const today = beijingDateStr(new Date())
  const stored = sessionStorage.getItem('sale_order_seq')
  let seq = 1
  if (stored) {
    const [savedDate, savedSeq] = stored.split('-')
    if (savedDate === today) {
      seq = parseInt(savedSeq) + 1
    }
  }
  sessionStorage.setItem('sale_order_seq', `${today}-${seq}`)
  return `${today}${seq.toString().padStart(3, '0')}`
}

/**
 * 将后端返回的 UTC ISO 字符串转换为北京时间显示格式 YYYY-MM-DD HH:MM
 * 后端 SQLite CURRENT_TIMESTAMP 为 UTC，前端展示需要 +8 小时
 */
function formatBeijingTime(isoStr: string | null | undefined): string {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  if (isNaN(d.getTime())) return ''
  const y = d.getFullYear()
  const m = (d.getMonth() + 1).toString().padStart(2, '0')
  const day = d.getDate().toString().padStart(2, '0')
  const h = d.getHours().toString().padStart(2, '0')
  const min = d.getMinutes().toString().padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}

// Member selector
const selectedMemberId = ref<number | null>(null)
const selectedMemberName = ref('')
const memberSearch = ref('')
const memberList = ref<{id:number, name:string, phone:string}[]>([])
const showMemberPicker = ref(false)
let memberSearchTimer: ReturnType<typeof setTimeout> | null = null

function onMemberSearch() {
  if (memberSearchTimer) clearTimeout(memberSearchTimer)
  memberSearchTimer = setTimeout(async () => {
    const kw = memberSearch.value.trim()
    if (!kw) { memberList.value = []; return }
    try {
      const res = await fetch(`${API}/members?keyword=${encodeURIComponent(kw)}&page_size=20`)
      const data = await res.json()
      memberList.value = data.items
    } catch { memberList.value = [] }
  }, 300)
}

function selectMember(m: {id:number, name:string, phone:string}) {
  selectedMemberId.value = m.id
  selectedMemberName.value = `${m.name} (${m.phone})`
  showMemberPicker.value = false
  memberSearch.value = ''
  memberList.value = []
}

function clearMember() {
  selectedMemberId.value = null
  selectedMemberName.value = ''
}

async function returnOrder(order: CompletedOrder) {
  if (!confirm(`确认退货：${order.order_number} ￥${order.actual_amount}？\n退货后库存将自动恢复。`)) return
  try {
    const res = await fetch(`${API}/sale-orders/${order.id}/return`, { method: 'POST' })
    if (res.ok) {
      showSuccessToast('退货完成')
      fetchCompletedOrders()
    } else {
      const err = await res.json()
      showToast(err.detail || '退货失败')
    }
  } catch { showToast('网络错误') }
}

function getCurrentMonth(): string {
  const d = new Date()
  return `${d.getFullYear()}${(d.getMonth() + 1).toString().padStart(2, '0')}`
}

const orderNumber = ref('')
const pendingList = ref<PendingItem[]>([])
const confirmedOrders = ref<CompletedOrder[]>([])
const currentMonth = ref(getCurrentMonth())
const isOnline = ref(navigator.onLine)

// Scan barcode popup
const showScanDialog = ref(false)
const scanBarcodeInput = ref('')
const scanCameraOpen = ref(false)
let scanTimer: ReturnType<typeof setTimeout> | null = null

window.addEventListener('online', () => (isOnline.value = true))
window.addEventListener('offline', () => (isOnline.value = false))

const totalAmount = computed(() =>
  pendingList.value.reduce((s, i) => s + i.unit_price * i.quantity, 0)
)

// --- 已出库清单 ---

async function fetchCompletedOrders() {
  if (!isOnline.value) return
  try {
    const res = await fetch(`${API}/sale-orders?month=${currentMonth.value}&page_size=50`)
    const data = await res.json()
    confirmedOrders.value = data.items || []
  } catch { /* 忽略 */ }
}

function prevMonth() {
  const y = parseInt(currentMonth.value.slice(0, 4))
  const m = parseInt(currentMonth.value.slice(4, 6))
  const d = new Date(y, m - 2, 1)  // Last month
  currentMonth.value = `${d.getFullYear()}${(d.getMonth() + 1).toString().padStart(2, '0')}`
  confirmedOrders.value = []
  fetchCompletedOrders()
}

function nextMonth() {
  const m = currentMonth.value
  const next = getCurrentMonth()
  if (m >= next) return  // Cannot exceed current month
  const y = parseInt(m.slice(0, 4))
  const mn = parseInt(m.slice(4, 6))
  const d = new Date(y, mn, 1)  // Next month
  currentMonth.value = `${d.getFullYear()}${(d.getMonth() + 1).toString().padStart(2, '0')}`
  confirmedOrders.value = []
  fetchCompletedOrders()
}

// Check for month rollover at 7AM on the 1st; auto-switch to new month
function checkMonthRollover() {
  const now = new Date()
  const newMonth = `${now.getFullYear()}${(now.getMonth() + 1).toString().padStart(2, '0')}`
  const storedMonth = sessionStorage.getItem('sale_display_month')

  if (storedMonth && storedMonth !== newMonth) {
    // Month rollover: clear last month display, load new month
    confirmedOrders.value = []
    currentMonth.value = newMonth
    fetchCompletedOrders()
  }
  sessionStorage.setItem('sale_display_month', newMonth)
}

// Periodic month rollover check (every minute)
let monthCheckTimer: ReturnType<typeof setInterval> | null = null

// --- 扫码弹窗 ---

function openScanDialog() {
  showScanDialog.value = true
  scanBarcodeInput.value = ''
  scanCameraOpen.value = false
  nextTick(() => {
    const input = document.querySelector('.sale-scan-input-wrapper input') as HTMLInputElement | null
    if (input) {
      input.focus()
      input.click()
    }
  })
}

function closeScanDialog() {
  showScanDialog.value = false
  stopCamera()
}

async function handleScanEnter() {
  if (!scanBarcodeInput.value) return
  const code = scanBarcodeInput.value.trim().toUpperCase()
  scanBarcodeInput.value = ''
  await lookupProduct(code)
}

watch(scanBarcodeInput, (val) => {
  if (scanTimer) clearTimeout(scanTimer)
  if (!val || !showScanDialog.value) return
  scanTimer = setTimeout(() => {
    if (scanBarcodeInput.value) handleScanEnter()
  }, 150)
})

function onScannerBarcode(barcode: string) {
  if (!showScanDialog.value) return
  scanBarcodeInput.value = barcode
  handleScanEnter()
}

async function lookupProduct(code: string) {
  if (isOnline.value) {
    try {
      const res = await fetch(`${API}/products?keyword=${code}&page_size=1`)
      const data = await res.json()
      if (data.items.length > 0) {
        addToPendingList(data.items[0])
        return
      }
      showToast('未找到商品')
      return
    } catch { /* 走离线 */ }
  }

  const results = await findProductOffline(code)
  if (results.length > 0) {
    addToPendingList(results[0])
  } else {
    showToast('未找到商品')
  }
}

function addToPendingList(p: any) {
  if (!orderNumber.value) {
    orderNumber.value = generateOrderNumber()
  }
  const existing = pendingList.value.find((i) => i.product_id === p.id)
  if (existing) {
    existing.quantity++
    showToast(`${p.name} x${existing.quantity}`)
  } else {
    pendingList.value.push({
      product_id: p.id,
      product_name: p.name,
      sku_code: p.sku_code || '',
      barcode: p.barcode || '',
      spec: p.spec || '',
      quantity: 1,
      unit_price: p.retail_price || 0,
    })
    showToast(p.name)
  }
  playBeep()
}

function removePendingItem(idx: number) {
  pendingList.value.splice(idx, 1)
  if (pendingList.value.length === 0) {
    orderNumber.value = ''
  }
}

// --- 摄像头扫码 ---

async function onOpenCamera() {
  scanCameraOpen.value = true
  // Use nextTick to preserve user gesture context (setTimeout breaks getUserMedia activation chain on mobile)
  await nextTick()
  const ok = await startCamera('sale-camera-scanner', (barcode: string) => {
    scanCameraOpen.value = false
    onScannerBarcode(barcode)
  })
  if (!ok) {
    scanCameraOpen.value = false
    showToast('无法打开摄像头，请检查摄像头权限')
  }
}

function onCloseCamera() {
  stopCamera()
  scanCameraOpen.value = false
}

// --- 确认出库 ---

async function confirmOutbound() {
  if (pendingList.value.length === 0) {
    showToast('请扫码添加商品')
    return
  }

  const payload: any = {
    items: pendingList.value.map((i) => ({
      product_id: i.product_id,
      quantity: i.quantity,
      unit_price: i.unit_price,
    })),
    discount: 0,
  }
  if (selectedMemberId.value) {
    payload.member_id = selectedMemberId.value
  }

  if (isOnline.value) {
    try {
      const res = await fetch(`${API}/sale-orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        const data = await res.json()
        showSuccessToast(`出库成功 单号${data.order_number} 总价￥${data.actual_amount.toFixed(0)}`)
        // Clear pending-out list, refresh shipped list
        pendingList.value = []
        orderNumber.value = ''
        closeScanDialog()
        await fetchCompletedOrders()
        return
      } else {
        const err = await res.json().catch(() => ({}))
        showToast(err.detail || '出库失败')
        return
      }
    } catch {
      /* 走离线 */
    }
  }

  await queueOperation('sale_order_create', payload)
  showSuccessToast('已暂存，联网后自动同步')
  pendingList.value = []
  orderNumber.value = ''
  closeScanDialog()
}

// Current month label
const currentMonthLabel = computed(() => {
  const m = currentMonth.value
  return `${m.slice(0, 4)}年${parseInt(m.slice(4, 6))}月`
})

onMounted(() => {
  startScan(onScannerBarcode)
  fetchCompletedOrders()
  checkMonthRollover()
  monthCheckTimer = setInterval(checkMonthRollover, 60000)
})

onUnmounted(() => {
  stopScan()
  stopCamera()
  if (monthCheckTimer) clearInterval(monthCheckTimer)
})
</script>

<template>
  <div class="page">
    <van-nav-bar title="销售开单" fixed placeholder />

    <!-- 扫码入口 -->
    <div style="padding:16px 16px 0;text-align:center">
      <van-button type="primary" size="large" icon="scan" round block @click="openScanDialog">
        扫码添加商品
      </van-button>
    </div>

    <!-- 扫码弹窗 -->
    <van-popup v-model:show="showScanDialog" position="bottom"
      :style="{ borderRadius: '16px 16px 0 0', maxHeight: '44vh', padding: '0' }"
      :lock-scroll="true" :close-on-click-overlay="true" teleport="body"
      @close="closeScanDialog">
      <div style="padding:24px 20px 20px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <span style="font-size:17px;font-weight:bold">扫码添加商品</span>
          <van-icon name="cross" size="20" @click="closeScanDialog" style="color:#999;cursor:pointer" />
        </div>

        <div class="sale-scan-input-wrapper" @keydown.enter.prevent="handleScanEnter">
          <van-field v-model="scanBarcodeInput" placeholder="扫描条码或手动输入后按回车"
            left-icon="scan" clearable style="width:100%" />
        </div>

        <div v-if="!scanCameraOpen" style="text-align:center;margin-top:12px">
          <van-button icon="photograph" round type="default" size="small" @click="onOpenCamera">
            摄像头扫码
          </van-button>
        </div>

        <div v-show="scanCameraOpen" style="margin-top:12px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <span style="font-size:15px;font-weight:bold;color:#1989fa">
              <van-loading type="spinner" size="16" style="vertical-align:middle;margin-right:6px" />
              正在扫描...
            </span>
            <span style="font-size:13px;color:#ee0a24;cursor:pointer" @click="onCloseCamera">关闭</span>
          </div>
          <div id="sale-camera-scanner" style="width:100%;height:36vh;border-radius:8px;overflow:hidden"></div>
        </div>
      </div>
    </van-popup>

    <!-- 待出库清单 -->
    <div v-if="pendingList.length > 0" style="padding:16px 16px 0">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h3 style="margin:0;font-size:16px">待出库清单</h3>
        <span style="color:#1989fa;font-size:14px;font-weight:bold">单号: {{ orderNumber }}</span>
      </div>

      <div v-for="(item, idx) in pendingList" :key="item.product_id"
        style="background:#fff;border-radius:8px;padding:12px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,0.06)">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:bold;font-size:15px;flex:1">{{ item.product_name }}</span>
          <van-icon name="delete-o" @click="removePendingItem(idx)" style="color:#ee0a24;cursor:pointer;font-size:18px" />
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:8px;color:#666;font-size:13px">
          <span>店内码: {{ item.barcode }}</span>
          <span>产品编码: {{ item.barcode }}</span>
          <span v-if="item.spec">规格: {{ item.spec }}</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px">
          <div style="display:flex;align-items:center;gap:8px">
            <span style="color:#999;font-size:13px">数量</span>
            <van-stepper v-model="item.quantity" min="1" max="999" integer style="transform:scale(0.85)" />
          </div>
          <div style="display:flex;align-items:center;gap:6px">
            <span style="color:#999;font-size:13px">单价</span>
            <input v-model.number="item.unit_price" type="number" min="0" step="0.01"
              style="width:72px;border:1px solid #ebedf0;border-radius:4px;padding:4px 8px;text-align:center;font-size:14px" />
            <span style="color:#ee0a24;font-weight:bold;font-size:15px;min-width:50px;text-align:right">
              ￥{{ (item.unit_price * item.quantity).toFixed(0) }}
            </span>
          </div>
        </div>
      </div>

      <div style="background:#fff;border-radius:8px;padding:16px;margin-top:8px;box-shadow:0 1px 4px rgba(0,0,0,0.06)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <span style="font-size:15px">合计</span>
          <span style="color:#ee0a24;font-size:22px;font-weight:bold">￥{{ totalAmount.toFixed(0) }}</span>
        </div>
        <!-- 会员选择 -->
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;padding:8px 12px;background:#f8f8f8;border-radius:8px">
          <span style="font-size:13px;color:#666;white-space:nowrap">会员：</span>
          <span v-if="selectedMemberName" style="flex:1;font-size:14px">{{ selectedMemberName }}</span>
          <span v-else style="flex:1;font-size:13px;color:#999">未选择</span>
          <van-button size="mini" plain @click="showMemberPicker=true">选择</van-button>
          <van-button v-if="selectedMemberId" size="mini" plain type="danger" @click="clearMember">清除</van-button>
        </div>
        <!-- 会员搜索弹窗 -->
        <van-popup v-model:show="showMemberPicker" position="bottom" round :style="{ height:'60vh',maxWidth:'480px',margin:'0 auto' }">
          <div style="padding:16px;overflow-y:auto;height:100%">
            <h3 style="margin:0 0 12px">选择会员</h3>
            <van-search v-model="memberSearch" shape="round" placeholder="搜索姓名/手机号" @update:model-value="onMemberSearch" />
            <div v-if="memberList.length===0 && memberSearch" style="text-align:center;color:#999;padding:20px">无匹配会员</div>
            <van-cell v-for="m in memberList" :key="m.id" :title="m.name" :label="m.phone" is-link @click="selectMember(m)" />
          </div>
        </van-popup>
        <van-button type="danger" block size="large" round @click="confirmOutbound">
          {{ isOnline ? '确认出库' : '暂存（离线）' }}
        </van-button>
      </div>
    </div>

    <!-- 已出库清单 -->
    <div style="padding:16px 16px 0">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h3 style="margin:0;font-size:16px">已出库清单</h3>
        <div style="display:flex;align-items:center;gap:4px">
          <van-icon name="arrow-left" @click="prevMonth" style="cursor:pointer;color:#666" />
          <span style="color:#999;font-size:13px;min-width:72px;text-align:center">{{ currentMonthLabel }}</span>
          <van-icon name="arrow" @click="nextMonth" style="cursor:pointer;color:#666" />
        </div>
      </div>

      <!-- PC 表格视图 -->
      <div v-if="isPC && confirmedOrders.length > 0" class="data-table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width:100px">单据编号</th>
              <th>商品明细</th>
              <th style="width:72px">数量</th>
              <th style="width:72px">单价</th>
              <th style="width:72px">小计</th>
              <th style="width:110px">出库时间</th>
              <th v-if="confirmedOrders.some(o => o.status !== '已退货')" style="width:60px">操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="order in confirmedOrders" :key="order.id">
              <tr v-for="(item, iidx) in order.items" :key="`${order.id}-${item.id}`"
                :class="{ 'order-first-row': iidx === 0 }">
                <td v-if="iidx === 0" :rowspan="order.items.length"
                  style="font-weight:bold;color:#1989fa;vertical-align:middle;cursor:pointer"
                  @click="viewOrderDetail(order)">
                  {{ order.order_number }}
                </td>
                <td>{{ item.product_name }}</td>
                <td>{{ item.quantity }}</td>
                <td>￥{{ item.unit_price.toFixed(0) }}</td>
                <td style="color:#ee0a24">￥{{ (item.quantity * item.unit_price).toFixed(0) }}</td>
                <td v-if="iidx === 0" :rowspan="order.items.length"
                  style="font-size:12px;color:#999;vertical-align:middle">
                  {{ formatBeijingTime(order.created_at) }}
                </td>
                <td v-if="iidx === 0 && order.status !== '已退货'"
                  :rowspan="order.items.length" style="vertical-align:middle">
                  <van-button size="mini" type="danger" @click="returnOrder(order)">退货</van-button>
                </td>
                <td v-else-if="iidx === 0" :rowspan="order.items.length"
                  style="font-size:12px;color:#999;vertical-align:middle">已退</td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- 移动端卡片视图 -->
      <template v-else>
        <div v-if="confirmedOrders.length === 0" style="text-align:center;padding:20px;color:#999">
          <p style="font-size:14px">暂无出库记录</p>
          <p style="font-size:12px">确认出库后将在此展示当月数据</p>
        </div>

        <div v-for="order in confirmedOrders" :key="order.id"
          style="background:#fff;border-radius:8px;padding:12px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,0.06)">
          <!-- 头部 -->
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <span style="font-weight:bold;color:#1989fa;cursor:pointer;text-decoration:underline" @click="viewOrderDetail(order)">{{ order.order_number }}</span>
            <span style="color:#ee0a24;font-weight:bold;font-size:17px">￥{{ order.actual_amount.toFixed(0) }}</span>
          </div>
          <!-- 商品列表 -->
          <div v-for="item in order.items" :key="item.id"
            style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px dashed #f0f0f0;font-size:13px">
            <span style="flex:1">{{ item.product_name }}</span>
            <span style="color:#999;margin:0 8px">x{{ item.quantity }}</span>
            <span>￥{{ (item.quantity * item.unit_price).toFixed(0) }}</span>
          </div>
          <!-- 时间 -->
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px">
            <span style="color:#999;font-size:12px">{{ formatBeijingTime(order.created_at) }}</span>
            <van-button v-if="order.status !== '已退货'" size="mini" type="danger" @click="returnOrder(order)">退货</van-button>
            <span v-else style="color:#999;font-size:12px">已退</span>
          </div>
        </div>
      </template>
    </div>

    <!-- 空状态 -->
    <div v-if="pendingList.length === 0 && confirmedOrders.length === 0"
      style="text-align:center;padding:60px 20px;color:#999">
      <van-icon name="scan" size="48" style="margin-bottom:16px;display:block" />
      <p>点击上方按钮扫码添加商品</p>
      <p style="font-size:13px">支持 USB 扫码枪或手机摄像头扫码</p>
    </div>
  </div>

  <!-- 订单详情弹窗 -->
  <van-popup v-model:show="showOrderDetail" position="bottom" round :style="{ height:'60vh',maxWidth:'520px',margin:'0 auto' }">
    <div v-if="detailOrder" style="padding:20px;overflow-y:auto;height:100%">
      <h3 style="margin:0 0 16px;font-size:18px">订单详情 — {{ detailOrder.order_number }}</h3>
      <van-cell-group inset style="margin-bottom:12px">
        <van-cell title="单据编号" :value="detailOrder.order_number" />
        <van-cell title="会员" :value="detailOrder.member_name || '无'" />
        <van-cell title="状态" :value="detailOrder.status" />
        <van-cell title="总金额" :value="'￥' + detailOrder.total_amount" />
        <van-cell title="实收" :value="'￥' + detailOrder.actual_amount" />
        <van-cell title="时间" :value="formatBeijingTime(detailOrder.created_at)" />
      </van-cell-group>
      <h4 style="margin:12px 0 8px;font-size:15px">商品明细</h4>
      <div v-for="(item, idx) in detailOrder.items" :key="idx" style="padding:8px 12px;border-bottom:1px solid #f0f0f0;font-size:13px">
        <div style="display:flex;justify-content:space-between">
          <span>{{ item.product_name }}</span>
          <span style="color:#666">￥{{ item.unit_price }} x {{ item.quantity }}</span>
        </div>
      </div>
    </div>
  </van-popup>
</template>

<style scoped>
.data-table-wrap {
  overflow-x: auto;
  margin-bottom: 16px;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}
.data-table th {
  background: #f5f7fa;
  color: #666;
  font-weight: 600;
  padding: 10px 8px;
  text-align: left;
  white-space: nowrap;
  border-bottom: 2px solid #e8e8e8;
}
.data-table td {
  padding: 10px 8px;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: middle;
}
.data-table tbody tr:hover {
  background: #f9fafb;
}
.order-first-row td {
  border-top: 2px solid #e8e8e8;
}
</style>
