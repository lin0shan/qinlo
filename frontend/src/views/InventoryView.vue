<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { findProductOffline } from '../db/cache'
import { useScanner } from '../composables/useScanner'
import { useLayout } from '../composables/useLayout'

const API = '/api/v1'
const { startScan, stopScan, startCamera, stopCamera, playBeep } = useScanner()

interface InventoryItem {
  product_id: number; product_name: string; barcode: string; sku_code: string; spec: string
  brand: string; category: string; unit: string; retail_price: number; safety_stock: number
  current_stock: number; status: string; image_url: string
}

const items = ref<InventoryItem[]>([])
const keyword = ref('')
const page = ref(1)
const loading = ref(false)
const refreshing = ref(false)
const total = ref(0)

// ---- 扫码入库弹窗 ----
const showScanDialog = ref(false)
const scanStep = ref<'scan' | 'confirm'>('scan')
const scanBarcodeInput = ref('')
const scannedProduct = ref<{ id: number; name: string } | null>(null)
const inboundQuantity = ref(1)
const scanCameraOpen = ref(false)

const statusColor: Record<string, string> = { normal: '#07c160', warning: '#ff976a', shortage: '#ee0a24' }
const invCategories = ['全部', '护肤', '彩妆', '香水', '工具', '其他']
const activeCat = ref('')
const invBrands = ref<string[]>(['全部'])
const activeBrand = ref('')

async function fetchInventory(showRefresh = false) {
  loading.value = true
  if (showRefresh) refreshing.value = true
  try {
    const params = new URLSearchParams({ page: String(page.value), page_size: '20' })
    if (keyword.value) params.set('keyword', keyword.value)
    if (activeCat.value) params.set('category', activeCat.value)
    if (activeBrand.value) params.set('brand', activeBrand.value)
    const res = await fetch(`${API}/inventory?${params}`)
    const data = await res.json()
    items.value = data.items
    total.value = data.total
  } catch {
    const cached = await findProductOffline(keyword.value)
    items.value = cached.map((p) => ({
      product_id: p.id, product_name: p.name, barcode: p.barcode, spec: p.spec,
      category: p.category, unit: p.unit, retail_price: p.retail_price,
      safety_stock: p.safety_stock, current_stock: p.current_stock,
      status: p.current_stock <= 0 ? 'shortage' : p.current_stock <= p.safety_stock ? 'warning' : 'normal',
      image_url: p.image_url,
    })) as any
    total.value = cached.length
  }
  loading.value = false
  refreshing.value = false
}

async function onLoadMore() {
  if (items.value.length >= total.value) return
  page.value++
  loading.value = true
  try {
    const params = new URLSearchParams({ page: String(page.value), page_size: '20' })
    if (keyword.value) params.set('keyword', keyword.value)
    if (activeCat.value) params.set('category', activeCat.value)
    if (activeBrand.value) params.set('brand', activeBrand.value)
    const res = await fetch(`${API}/inventory?${params}`)
    const data = await res.json()
    items.value = [...items.value, ...data.items]
    total.value = data.total
  } catch { /* ignore */ }
  loading.value = false
}

async function openScanDialog() {
  scanStep.value = 'scan'
  scanBarcodeInput.value = ''
  scannedProduct.value = null
  inboundQuantity.value = 1
  scanCameraOpen.value = false
  showScanDialog.value = true
  await nextTick()
  // 自动聚焦输入框，确保扫码枪输入能进入 van-field 内部 input
  const input = document.querySelector('.scan-input-wrapper input') as HTMLInputElement | null
  if (input) {
    input.focus()
    // 有些扫码枪需要点击事件触发焦点，这里再点一下确保
    input.click()
  }
}

function onSearch() { page.value = 1; fetchInventory() }
function onRefresh() { page.value = 1; fetchInventory(true) }
function onCatClick(cat: string) {
  activeCat.value = activeCat.value === cat ? '' : cat
  page.value = 1
  fetchInventory()
}
function onBrandClick(brand: string) {
  activeBrand.value = activeBrand.value === brand ? '' : brand
  page.value = 1
  fetchInventory()
}

// debounce: 输入停止 150ms 后自动触发
let scanTimer: ReturnType<typeof setTimeout> | null = null
watch(scanBarcodeInput, (val) => {
  if (scanTimer) clearTimeout(scanTimer)
  if (!val || scanStep.value !== 'scan') return
  scanTimer = setTimeout(() => {
    handleScanEnter()
  }, 150)
})

async function handleScanEnter() {
  if (!scanBarcodeInput.value) return
  const code = scanBarcodeInput.value
  scanBarcodeInput.value = ''
  await lookupInDialog(code)
}

async function lookupInDialog(code: string) {
  if (!code.trim()) return
  scanCameraOpen.value = false
  stopCamera()
  try {
    const res = await fetch(`${API}/products?keyword=${code}&page_size=1`)
    const data = await res.json()
    if (data.items.length > 0) {
      const p = data.items[0]
      scannedProduct.value = { id: p.id, name: p.name }
      inboundQuantity.value = 1
      scanStep.value = 'confirm'
      playBeep()
      return
    }
  } catch {
    const cached = await findProductOffline(code)
    if (cached.length > 0) {
      scannedProduct.value = { id: cached[0].id, name: cached[0].name }
      inboundQuantity.value = 1
      scanStep.value = 'confirm'
      playBeep()
      return
    }
  }
  showToast('该条码未配置，请到商品管理页配置后重新扫码')
}

async function confirmInbound() {
  if (!scannedProduct.value || inboundQuantity.value <= 0) {
    showToast('请输入入库数量')
    return
  }
  const res = await fetch(`${API}/inventory/inbound`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      product_id: scannedProduct.value.id,
      quantity: inboundQuantity.value,
    }),
  })
  if (res.ok) {
    const data = await res.json()
    showSuccessToast(data.message)
    scanStep.value = 'scan'
    scanBarcodeInput.value = ''
    scannedProduct.value = null
    inboundQuantity.value = 1
    fetchInventory()
    // 不关闭弹窗，继续扫下一个
  } else {
    showToast('入库失败')
  }
}

// 摄像头（仅移动端，弹窗内）
async function openScanCamera() {
  scanCameraOpen.value = true
  // 使用 nextTick 保持用户手势上下文（setTimeout 会断掉移动端 getUserMedia 的激活链）
  await nextTick()
  const ok = await startCamera('scan-dialog-camera', (barcode: string) => {
    scanBarcodeInput.value = barcode
    handleScanEnter()
  })
  if (!ok) {
    scanCameraOpen.value = false
    showToast('无法打开摄像头，请检查摄像头权限')
  }
}

function closeScanDialog() {
  scanCameraOpen.value = false
  stopCamera()
  showScanDialog.value = false
}

// USB 扫码枪：仅弹窗打开时接收，避免页面级误触发
function onScannerBarcode(barcode: string) {
  if (!showScanDialog.value || scanStep.value !== 'scan') return
  scanBarcodeInput.value = barcode
  handleScanEnter()
}

const { isPC } = useLayout()

// ---- 库存日志弹窗 ----
interface LogEntry { id: number; product_id: number; product_name: string; change_type: string; change_quantity: number; after_quantity: number; reference_id: number; reference_type: string; created_at: string }
const showLogDialog = ref(false)
const logItems = ref<LogEntry[]>([])
const logProductName = ref('')
const logLoading = ref(false)

async function openLogDialog(pid: number, pname: string) {
  logProductName.value = pname
  showLogDialog.value = true
  logLoading.value = true
  try {
    const res = await fetch(`${API}/inventory/logs?product_id=${pid}&page_size=200`)
    const data = await res.json()
    logItems.value = data.items
  } catch { logItems.value = [] }
  logLoading.value = false
}

// ---- 盘点弹窗 ----
const showCheckDialog = ref(false)
const checkProductId = ref(0)
const checkProductName = ref('')
const checkSystemStock = ref(0)
const checkActualQty = ref('')

function openCheckDialog(pid: number, pname: string, stock: number) {
  checkProductId.value = pid
  checkProductName.value = pname
  checkSystemStock.value = stock
  checkActualQty.value = String(stock)
  showCheckDialog.value = true
}

async function submitCheck() {
  const actual = parseInt(checkActualQty.value)
  if (isNaN(actual)) { showToast('请输入有效数量'); return }
  try {
    const res = await fetch(`${API}/inventory/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: [{ product_id: checkProductId.value, actual_quantity: actual }] }),
    })
    if (!res.ok) { const e = await res.json(); showToast(e.detail || '盘点失败'); return }
    showSuccessToast('盘点完成')
    showCheckDialog.value = false
    page.value = 1
    items.value = []
    total.value = 0
    fetchInventory()
  } catch { showToast('网络错误') }
}

async function fetchBrands() {
  try {
    const res = await fetch(`${API}/brands`)
    const brands = await res.json()
    invBrands.value = ['全部', ...brands]
  } catch { /* keep default */ }
}

onMounted(() => { fetchBrands(); fetchInventory(); startScan(onScannerBarcode) })
onUnmounted(() => { stopScan(); stopCamera(); closeScanDialog() })
</script>

<template>
  <div class="page">
    <van-nav-bar title="库存看板" fixed placeholder />
    <van-search v-model="keyword" placeholder="搜索商品" @search="onSearch" />
    <van-button type="primary" block @click="openScanDialog" style="margin:0 16px 8px">入库</van-button>

    <!-- 扫码入库弹窗 -->
    <van-popup v-model:show="showScanDialog" position="bottom" :style="{ height: '70%' }" round @close="closeScanDialog">
      <van-nav-bar title="扫码入库" left-text="关闭" @click-left="closeScanDialog" />

      <!-- 扫码步骤 -->
      <div v-if="scanStep === 'scan'" style="padding:16px;display:flex;flex-direction:column;align-items:center">
        <p style="font-size:16px;color:#333;margin:24px 0 16px">请扫码入库</p>
        <div class="scan-input-wrapper" @keydown.enter.prevent="handleScanEnter">
          <van-field v-model="scanBarcodeInput" placeholder="扫描条码或手动输入后按回车"
            left-icon="scan" clearable style="width:100%" />
        </div>
        <span v-if="isPC" style="font-size:12px;color:#999;margin-top:8px">USB 扫码枪已启用 — 直接扫码即可</span>
        <van-button v-else-if="!scanCameraOpen" icon="photograph" round type="primary" size="small"
          @click="openScanCamera" style="margin-top:12px">摄像头扫码</van-button>
        <!-- 摄像头渲染区 -->
        <div v-if="scanCameraOpen" style="margin-top:12px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <span style="font-size:13px;font-weight:bold;color:#1989fa">
              <van-loading type="spinner" size="14" style="vertical-align:middle;margin-right:6px" />
              正在扫描...
            </span>
            <span style="font-size:13px;color:#ee0a24;cursor:pointer" @click="stopCamera(); scanCameraOpen = false">关闭</span>
          </div>
          <div id="scan-dialog-camera"
            style="width:100%;height:200px;border-radius:8px;overflow:hidden"></div>
        </div>
      </div>

      <!-- 确认步骤 -->
      <div v-if="scanStep === 'confirm'" style="padding:16px">
        <van-cell :title="scannedProduct?.name" label="商品名称" />
        <van-field label="入库数量">
          <template #input>
            <van-stepper v-model="inboundQuantity" min="1" max="9999" integer style="float:right" />
          </template>
        </van-field>
        <div style="display:flex;gap:12px;margin-top:16px">
          <van-button plain @click="scanStep = 'scan'; scanCameraOpen = false; stopCamera()"
            style="flex:1">返回重新扫码</van-button>
          <van-button type="primary" @click="confirmInbound" style="flex:1">确认入库</van-button>
        </div>
      </div>
    </van-popup>

    <!-- 分类筛选 -->
    <div class="filter-bar">
      <span v-for="c in invCategories" :key="c"
        class="filter-tag"
        :class="{ active: activeCat === c || (c === '全部' && !activeCat) }"
        @click="onCatClick(c === '全部' ? '' : c)"
      >{{ c }}</span>
    </div>

    <!-- 品牌筛选 -->
    <div class="filter-bar">
      <span v-for="b in invBrands" :key="b"
        class="filter-tag"
        :class="{ active: activeBrand === b || (b === '全部' && !activeBrand) }"
        @click="onBrandClick(b === '全部' ? '' : b)"
      >{{ b }}</span>
    </div>

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh" success-text="刷新成功">
      <van-list v-model:loading="loading" :finished="items.length >= total" finished-text="没有更多了" @load="onLoadMore">

        <!-- PC 表格视图 -->
        <div v-if="isPC" class="data-table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width:3%">#</th>
                <th style="width:5%">品牌</th>
                <th>商品名</th>
                <th style="width:7%">产品编码</th>
                <th style="width:5%">规格</th>
                <th style="width:4%">分类</th>
                <th style="width:3%">单位</th>
                <th style="width:6%">零售价</th>
                <th style="width:5%">安全库存</th>
                <th style="width:6%">当前库存</th>
                <th style="width:5%">状态</th>
                <th style="width:8%">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in items" :key="item.product_id">
                <td>{{ idx + 1 }}</td>
                <td>{{ item.brand || '-' }}</td>
                <td><span class="cell-name">{{ item.product_name }}</span></td>
                <td><code class="cell-code">{{ item.barcode || '-' }}</code></td>
                <td>{{ item.spec || '-' }}</td>
                <td>{{ item.category }}</td>
                <td>{{ item.unit }}</td>
                <td class="num-cell">￥{{ item.retail_price }}</td>
                <td class="num-cell">{{ item.safety_stock }}</td>
                <td><van-tag :color="statusColor[item.status]" size="large" style="min-width:44px;text-align:center">{{ item.current_stock }}</van-tag></td>
                <td>
                  <van-tag :color="statusColor[item.status]" size="medium" style="min-width:44px;text-align:center">
                    {{ item.status === 'normal' ? '正常' : item.status === 'warning' ? '预警' : '缺货' }}
                  </van-tag>
                </td>
                <td>
                  <van-button size="mini" @click="openLogDialog(item.product_id, item.product_name)">日志</van-button>
                  <van-button size="mini" type="warning" @click="openCheckDialog(item.product_id, item.product_name, item.current_stock)">盘点</van-button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 移动端列表视图 -->
        <template v-else>
        <van-cell v-for="(item, idx) in items" :key="item.product_id"
          :title="`${idx + 1}. ${item.product_name}`"
          :label="`${item.brand ? item.brand + ' · ' : ''}${item.spec || ''}`" center>
          <template #icon>
            <van-tag :color="statusColor[item.status]" size="large" style="margin-right:10px;min-width:44px;text-align:center">
              {{ item.current_stock }}
            </van-tag>
          </template>
        </van-cell>
        </template>
      </van-list>
    </van-pull-refresh>

    <!-- 库存日志弹窗 -->
    <van-popup v-model:show="showLogDialog" position="bottom" round :style="{ height: '65vh', maxWidth: '520px', margin: '0 auto' }">
      <div style="padding:16px;overflow-y:auto;height:100%">
        <h3 style="margin:0 0 12px;font-size:16px">{{ logProductName }} — 库存日志</h3>
        <van-loading v-if="logLoading" style="margin:40px auto;display:block" />
        <div v-else-if="logItems.length===0" style="color:#999;text-align:center;padding:40px">暂无记录</div>
        <div v-else v-for="l in logItems" :key="l.id" style="padding:8px 0;border-bottom:1px solid #f0f0f0;font-size:13px">
          <div style="display:flex;justify-content:space-between">
            <span style="font-weight:600">{{ l.change_type }}</span>
            <span :style="{ color: l.change_quantity > 0 ? '#07c160' : '#ee0a24' }">
              {{ l.change_quantity > 0 ? '+' : '' }}{{ l.change_quantity }}
            </span>
          </div>
          <div style="color:#999;font-size:12px;margin-top:2px">
            变动后库存 {{ l.after_quantity }} · {{ l.created_at?.replace('T',' ').slice(0,19) || '' }}
          </div>
        </div>
      </div>
    </van-popup>

    <!-- 盘点弹窗 -->
    <van-popup v-model:show="showCheckDialog" position="bottom" round :style="{ maxWidth: '480px', margin: '0 auto' }">
      <div style="padding:20px">
        <h3 style="margin:0 0 12px;font-size:18px">盘点 — {{ checkProductName }}</h3>
        <van-cell title="系统库存" :value="String(checkSystemStock)" />
        <van-field v-model="checkActualQty" label="实际库存" type="digit" placeholder="输入实际数量" />
        <div style="display:flex;gap:12px;margin-top:16px">
          <van-button plain @click="showCheckDialog=false" style="flex:1">取消</van-button>
          <van-button type="warning" @click="submitCheck" style="flex:1">确认盘点</van-button>
        </div>
      </div>
    </van-popup>

  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  gap: 8px;
  padding: 8px 16px;
  overflow-x: auto;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
}
.filter-tag {
  flex-shrink: 0;
  padding: 4px 12px;
  border-radius: 14px;
  font-size: 13px;
  color: #666;
  background: #f5f5f5;
  cursor: pointer;
  transition: all 0.2s;
}
.filter-tag.active {
  color: #fff;
  background: #ff6b81;
}

/* PC DataTable */
.data-table-wrap {
  overflow-x: auto;
}
.data-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  font-size: 13px;
  background: #fff;
  border: 1px solid #d8d8d8;
  border-radius: 8px;
  overflow: hidden;
}
.data-table th {
  background: #f5f7fa;
  color: #555;
  font-weight: 600;
  padding: 10px 8px;
  text-align: left;
  white-space: nowrap;
  border: 1px solid #e0e0e0;
}
.data-table th:first-child {
  border-left: none;
}
.data-table td {
  padding: 10px 8px;
  border: 1px solid #e9e9e9;
  vertical-align: middle;
}
.data-table td:first-child {
  border-left: none;
}
.cell-name {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cell-code {
  display: inline-block;
  font-size: 12px;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  letter-spacing: 0.5px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.data-table tbody tr:nth-child(even) {
  background: #fafbfc;
}
.data-table tbody tr:hover {
  background: #edf4ff;
}
.num-cell {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
