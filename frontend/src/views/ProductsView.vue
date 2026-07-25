<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { showToast } from 'vant'
import { findProductOffline } from '../db/cache'
import { useBarcode } from '../composables/useBarcode'
import { useLayout } from '../composables/useLayout'

const API = '/api/v1'

interface Product {
  id: number; name: string; barcode: string; sku_code: string; spec: string; brand: string; category: string
  unit: string; cost_price: number; retail_price: number; wholesale_price: number
  safety_stock: number; status: string; current_stock: number; image_url: string; remark: string
}

const products = ref<Product[]>([])
const total = ref(0)
const keyword = ref('')
const page = ref(1)
const loading = ref(false)
const refreshing = ref(false)
const showForm = ref(false)
const editingId = ref<number | null>(null)

const form = ref({
  name: '', barcode: '', spec: '', brand: '', category: '护肤', unit: '瓶',
  cost_price: 0, retail_price: 0, safety_stock: 5, remark: '',
})

const categories = ['全部', '护肤', '彩妆', '香水', '工具', '其他']
const activeCategory = ref('')
const brands = ref<string[]>(['全部'])
const activeBrand = ref('')
const units = ['瓶', '盒', '支', '片', '个']

async function fetchProducts(showRefresh = false) {
  loading.value = true
  if (showRefresh) refreshing.value = true
  try {
    const params = new URLSearchParams({ page: String(page.value), page_size: '20' })
    if (keyword.value) params.set('keyword', keyword.value)
    if (activeCategory.value) params.set('category', activeCategory.value)
    if (activeBrand.value) params.set('brand', activeBrand.value)
    const res = await fetch(`${API}/products?${params}`)
    const data = await res.json()
    products.value = data.items
    total.value = data.total
  } catch {
    const cached = await findProductOffline(keyword.value)
    products.value = cached as any
    total.value = cached.length
  }
  loading.value = false
  refreshing.value = false
}

async function onLoad() {
  if (products.value.length >= total.value) return
  page.value++
  loading.value = true
  try {
    const params = new URLSearchParams({ page: String(page.value), page_size: '20' })
    if (keyword.value) params.set('keyword', keyword.value)
    if (activeCategory.value) params.set('category', activeCategory.value)
    if (activeBrand.value) params.set('brand', activeBrand.value)
    const res = await fetch(`${API}/products?${params}`)
    const data = await res.json()
    products.value = [...products.value, ...data.items]
    total.value = data.total
  } catch { /* ignore */ }
  loading.value = false
}

function onRefresh() { page.value = 1; fetchProducts(true) }

function onCategoryClick(cat: string) {
  activeCategory.value = activeCategory.value === cat ? '' : cat
  page.value = 1
  fetchProducts()
}

function onBrandClick(brand: string) {
  activeBrand.value = activeBrand.value === brand ? '' : brand
  page.value = 1
  fetchProducts()
}

function openCreate() {
  editingId.value = null
  form.value = { name: '', barcode: '', spec: '', brand: '', category: '护肤', unit: '瓶', cost_price: 0, retail_price: 0, safety_stock: 5, remark: '' }
  showForm.value = true
}

function openEdit(p: Product) {
  editingId.value = p.id
  form.value = {
    name: p.name, barcode: p.barcode || '', spec: p.spec || '', brand: p.brand || '',
    category: p.category, unit: p.unit, cost_price: p.cost_price, retail_price: p.retail_price,
    safety_stock: p.safety_stock, remark: p.remark || '',
  }
  showForm.value = true
}

async function saveProduct() {
  const url = editingId.value ? `${API}/products/${editingId.value}` : `${API}/products`
  const method = editingId.value ? 'PUT' : 'POST'
  const res = await fetch(url, {
    method, headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(form.value),
  })
  if (res.ok) {
    showToast(editingId.value ? '更新成功' : '创建成功')
    showForm.value = false
    fetchProducts()
  } else {
    const err = await res.json()
    showToast(err.detail || '操作失败')
  }
}

async function toggleStatus(p: Product) {
  const newStatus = p.status === '在售' ? '停售' : '在售'
  await fetch(`${API}/products/${p.id}/status?status=${encodeURIComponent(newStatus)}`, { method: 'PATCH' })
  fetchProducts()
}

// Barcode button removed (auto-assigned on create; editable manually)

function onSearch() { page.value = 1; fetchProducts() }

// ---- 条码预览 + 打印 ----

const { render: renderBarcode, print: printBarcode } = useBarcode()
const showBarcodePopup = ref(false)
const barcodeTarget = ref<{ name: string; barcode: string }>({ name: '', barcode: '' })

async function openBarcodePrint(name: string, barcode: string) {
  barcodeTarget.value = { name, barcode }
  showBarcodePopup.value = true
  await nextTick()
  renderBarcode('#barcode-canvas', barcode)
}

function doPrint() {
  printBarcode(barcodeTarget.value.barcode, barcodeTarget.value.name)
}

const catColor: Record<string, string> = { '护肤': '#1989fa', '彩妆': '#ee0a24', '香水': '#ff976a', '工具': '#07c160', '其他': '#999' }

const { isPC } = useLayout()

async function fetchBrands() {
  try {
    const res = await fetch(`${API}/brands`)
    const list = await res.json()
    brands.value = ['全部', ...list]
  } catch { /* keep default */ }
}

onMounted(() => {
  fetchBrands()
  fetchProducts()
})
</script>

<template>
  <div class="page">
    <van-nav-bar title="商品管理" fixed placeholder />
    <van-search v-model="keyword" placeholder="搜索商品名称/条码" @search="onSearch" />
    <van-button type="primary" block @click="openCreate" style="margin:0 16px 8px">新增商品</van-button>

    <!-- 分类筛选 -->
    <div class="filter-bar">
      <span v-for="c in categories" :key="c"
        class="filter-tag"
        :class="{ active: activeCategory === c || (c === '全部' && !activeCategory) }"
        @click="onCategoryClick(c === '全部' ? '' : c)"
      >{{ c }}</span>
    </div>

    <!-- 品牌筛选 -->
    <div class="filter-bar">
      <span v-for="b in brands" :key="b"
        class="filter-tag"
        :class="{ active: activeBrand === b || (b === '全部' && !activeBrand) }"
        @click="onBrandClick(b === '全部' ? '' : b)"
      >{{ b }}</span>
    </div>

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh" success-text="刷新成功">
      <van-list v-model:loading="loading" :finished="products.length >= total" finished-text="没有更多了" @load="onLoad">

        <!-- PC 表格视图 -->
        <div v-if="isPC" class="data-table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width:4%">#</th>
                <th style="width:6%">品牌</th>
                <th>商品名</th>
                <th style="width:8%">产品编码</th>
                <th style="width:5%">分类</th>
                <th style="width:9%">规格</th>
                <th style="width:7%">零售价</th>
                <th style="width:7%">成本价</th>
                <th style="width:5%">库存</th>
                <th style="width:5%">状态</th>
                <th style="width:12%">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(p, idx) in products" :key="p.id">
                <td>{{ idx + 1 }}</td>
                <td>{{ p.brand || '-' }}</td>
                <td><span class="cell-name">{{ p.name }}</span></td>
                <td><code class="cell-code">{{ p.barcode || '-' }}</code></td>
                <td><van-tag :color="catColor[p.category] || '#999'" size="medium">{{ p.category }}</van-tag></td>
                <td><span class="cell-name">{{ p.spec || '-' }}</span></td>
                <td class="num-cell">￥{{ p.retail_price }}</td>
                <td class="num-cell">￥{{ p.cost_price }}</td>
                <td :class="{ 'stock-warn': p.current_stock < p.safety_stock }">{{ p.current_stock }}</td>
                <td>
                  <van-tag v-if="p.status === '停售'" type="danger" size="medium">停售</van-tag>
                  <van-tag v-else-if="p.current_stock <= 0" type="danger" size="medium">缺货</van-tag>
                  <van-tag v-else-if="p.current_stock <= p.safety_stock" color="#ff976a" size="medium">低库存</van-tag>
                  <van-tag v-else type="success" size="medium">在售</van-tag>
                </td>
                <td>
                  <van-button size="mini" @click="openEdit(p)">编辑</van-button>
                  <van-button v-if="p.barcode" size="mini" type="warning" @click="openBarcodePrint(p.name, p.barcode)">打印</van-button>
                  <van-button size="mini" :type="p.status==='在售'?'danger':'primary'" @click="toggleStatus(p)">
                    {{ p.status === '在售' ? '停售' : '上架' }}
                  </van-button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 移动端卡片视图 -->
        <template v-else>
        <van-card v-for="(p, idx) in products" :key="p.id"
          :title="`${idx + 1}. ${p.name}`" :thumb="p.image_url || undefined">
          <template #desc>
            <van-tag :color="catColor[p.category] || '#999'" style="margin-right:6px">{{ p.category }}</van-tag>
            <span v-if="p.brand" style="color:#ff6b81;font-size:12px;margin-right:6px">{{ p.brand }}</span>
            <span style="color:#999;font-size:12px">{{ p.spec || '-' }} · {{ p.barcode || '-' }}</span>
          </template>
          <template #tags>
            <van-tag v-if="p.status === '停售'" type="danger">停售</van-tag>
            <van-tag v-else-if="p.current_stock <= 0" type="danger">缺货</van-tag>
            <van-tag v-else-if="p.current_stock <= p.safety_stock" color="#ff976a">低库存</van-tag>
          </template>
          <template #price>
            <span style="font-weight:700;font-size:16px">￥{{ p.retail_price }}</span>
            <span style="font-size:11px;color:#999;margin-left:4px">库存{{ p.current_stock }}</span>
          </template>
          <template #num>
            <span style="font-size:11px;color:#999">成本￥{{ p.cost_price }}</span>
          </template>
          <template #footer>
            <van-button size="mini" @click="openEdit(p)">编辑</van-button>
            <van-button v-if="p.barcode" size="mini" type="warning" @click="openBarcodePrint(p.name, p.barcode)">打印</van-button>
            <van-button size="mini" :type="p.status==='在售'?'danger':'primary'" @click="toggleStatus(p)">
              {{ p.status === '在售' ? '停售' : '上架' }}
            </van-button>
          </template>
        </van-card>
        </template>
      </van-list>
    </van-pull-refresh>

    <!-- 新增/编辑弹窗 -->
    <van-popup v-model:show="showForm" position="bottom" :style="{ height: '80%' }" round>
      <van-nav-bar :title="editingId ? '编辑商品' : '新增商品'" left-text="取消" @click-left="showForm = false" />
      <van-form @submit="saveProduct" style="padding:16px">
        <van-field v-model="form.name" label="名称" required placeholder="商品名称" />
        <van-field v-model="form.brand" label="品牌" placeholder="如 赫莲娜" />
        <van-field v-model="form.barcode" label="条码" placeholder="留空自动生成" />
        <van-field v-model="form.spec" label="规格" placeholder="如 230ml" />
        <van-field v-model="form.cost_price" label="成本价" type="number" />
        <van-field v-model="form.retail_price" label="零售价" type="number" />
        <van-field v-model="form.safety_stock" label="安全库存" type="digit" />
        <van-field name="category" label="分类">
          <template #input>
            <van-radio-group v-model="form.category" direction="horizontal">
              <van-radio v-for="c in categories" :key="c" :name="c">{{ c }}</van-radio>
            </van-radio-group>
          </template>
        </van-field>
        <van-field name="unit" label="单位">
          <template #input>
            <van-radio-group v-model="form.unit" direction="horizontal">
              <van-radio v-for="u in units" :key="u" :name="u">{{ u }}</van-radio>
            </van-radio-group>
          </template>
        </van-field>
        <van-field v-model="form.remark" label="备注" placeholder="选填" />
        <van-button type="primary" block native-type="submit" style="margin-top:16px">保存</van-button>
      </van-form>
    </van-popup>

    <!-- 条码预览 + 打印弹窗 -->
    <van-popup v-model:show="showBarcodePopup" :style="{ width: '90%', borderRadius: '12px' }" :close-on-click-overlay="true">
      <div style="padding:24px;text-align:center">
        <div style="font-size:16px;font-weight:600;margin-bottom:16px;color:#333">{{ barcodeTarget.name }}</div>
        <canvas id="barcode-canvas" style="max-width:100%"></canvas>
        <div style="font-size:13px;color:#888;margin-top:8px;letter-spacing:1px">{{ barcodeTarget.barcode }}</div>
        <van-button type="warning" block @click="doPrint" style="margin-top:16px">打印标签</van-button>
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
.stock-warn {
  color: #ee0a24;
  font-weight: 600;
}
</style>
