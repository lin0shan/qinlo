<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import DataTable from '../components/DataTable.vue'
import type { ColumnDef } from '../components/DataTable.vue'

const API = '/api/v1'

// Report type: sales / inbound
const reportType = ref<'sales' | 'inbound'>('sales')

// ==================== 销售报表 ====================
const salesLoading = ref(false)
const salesPeriod = ref<'daily' | 'monthly'>('daily')
const salesData = ref<any[]>([])
const salesSummary = ref<any>(null)

// ==================== 入库报表 ====================
const inboundLoading = ref(false)
const inboundPeriod = ref<'daily' | 'monthly'>('daily')
const inboundData = ref<any[]>([])
const inboundSummary = ref<any>(null)

// ==================== 排行 ====================
const rankLoading = ref(false)
const rankData = ref<any[]>([])
const rankLimit = ref(10)

// PC 检测
const isPC = computed(() => window.innerWidth >= 1280)

// ==================== API 调用 ====================
async function fetchSalesReport() {
  salesLoading.value = true
  try {
    const params = new URLSearchParams({ period: salesPeriod.value })
    const res = await fetch(`${API}/reports/sales?${params}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    salesData.value = data.items || []
    salesSummary.value = data.summary
  } catch (e) {
    console.error('获取销售报表失败:', e)
  } finally {
    salesLoading.value = false
  }
}

async function fetchInboundReport() {
  inboundLoading.value = true
  try {
    const params = new URLSearchParams({ period: inboundPeriod.value })
    const res = await fetch(`${API}/reports/inbound?${params}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    inboundData.value = data.items || []
    inboundSummary.value = data.summary
  } catch (e) {
    console.error('获取入库报表失败:', e)
  } finally {
    inboundLoading.value = false
  }
}

// 销售报表 → 热销排行；入库报表 → 库存排行
async function fetchRank() {
  rankLoading.value = true
  try {
    const endpoint = reportType.value === 'sales' ? 'top-products' : 'inventory-top'
    const res = await fetch(`${API}/reports/${endpoint}?limit=${rankLimit.value}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    rankData.value = data.items || []
  } catch (e) {
    console.error(`获取排行失败:`, e)
  } finally {
    rankLoading.value = false
  }
}

function switchReportType(type: 'sales' | 'inbound') {
  reportType.value = type
  if (type === 'sales' && salesData.value.length === 0) fetchSalesReport()
  if (type === 'inbound' && inboundData.value.length === 0) fetchInboundReport()
  fetchRank()
}

onMounted(() => {
  fetchSalesReport()
  fetchRank()
})

// ==================== 列定义 ====================
const salesColumns: ColumnDef[] = [
  { key: 'date', title: '日期', width: '120px' },
  { key: 'order_count', title: '订单数', align: 'center', sortable: true },
  { key: 'total_amount', title: '原价合计', align: 'right', sortable: true },
  { key: 'total_discount', title: '优惠', align: 'right' },
  { key: 'actual_amount', title: '实收', align: 'right', sortable: true },
]

const inboundColumns: ColumnDef[] = [
  { key: 'date', title: '日期', width: '120px' },
  { key: 'inbound_count', title: '入库笔数', align: 'center', sortable: true },
  { key: 'total_quantity', title: '入库数量', align: 'right', sortable: true },
]

const rankColumns = computed<ColumnDef[]>(() => {
  if (reportType.value === 'sales') {
    return [
      { key: 'product_name', title: '商品名称' },
      { key: 'total_quantity', title: '销量', align: 'center', sortable: true },
      { key: 'total_amount', title: '销售额', align: 'right', sortable: true },
    ]
  }
  return [
    { key: 'product_name', title: '商品名称' },
    { key: 'current_stock', title: '当前库存', align: 'center', sortable: true },
  ]
})

const rankTitle = computed(() => {
  return reportType.value === 'sales' ? '热销商品 TOP' : '库存商品 TOP'
})
</script>

<template>
  <div class="page">
    <van-nav-bar title="经营报表" fixed placeholder />

    <!-- 报表类型切换 -->
    <van-tabs v-model:active="reportType" @change="(name: string) => switchReportType(name as 'sales' | 'inbound')">
      <van-tab title="销售报表" name="sales" />
      <van-tab title="入库报表" name="inbound" />
    </van-tabs>

    <!-- ==================== 销售报表 ==================== -->
    <template v-if="reportType === 'sales'">
      <van-cell-group style="margin-bottom:8px">
        <van-cell title="销售报表">
          <template #right-icon>
            <van-button size="mini" @click="salesPeriod = salesPeriod === 'daily' ? 'monthly' : 'daily'; fetchSalesReport()">
              {{ salesPeriod === 'daily' ? '切换月报' : '切换日报' }}
            </van-button>
          </template>
        </van-cell>
      </van-cell-group>

      <!-- 汇总数值卡片 -->
      <div v-if="salesSummary" class="summary-cards">
        <div class="summary-card">
          <span class="sc-val">{{ salesSummary.total_orders }}</span>
          <span class="sc-label">订单数</span>
        </div>
        <div class="summary-card">
          <span class="sc-val">&yen;{{ salesSummary.total_amount }}</span>
          <span class="sc-label">原价合计</span>
        </div>
        <div class="summary-card highlight">
          <span class="sc-val">&yen;{{ salesSummary.total_actual }}</span>
          <span class="sc-label">实收金额</span>
        </div>
      </div>

      <!-- 移动端：卡片列表 -->
      <div v-if="!isPC && salesData.length > 0">
        <van-cell v-for="r in salesData" :key="r.date || `${r.year}-${r.month}`"
          :title="r.date || `${r.year}-${String(r.month).padStart(2,'0')}`"
          :label="`${r.order_count}笔 | 实收 ￥${r.actual_amount}`"
          value="" />
      </div>
      <!-- PC 端：DataTable -->
      <DataTable v-if="isPC" :columns="salesColumns" :data="salesData" :loading="salesLoading"
        empty-text="暂无销售数据" />
      <van-empty v-if="!salesLoading && salesData.length === 0" description="暂无销售数据" />
    </template>

    <!-- ==================== 入库报表 ==================== -->
    <template v-if="reportType === 'inbound'">
      <van-cell-group style="margin-bottom:8px">
        <van-cell title="入库报表">
          <template #right-icon>
            <van-button size="mini" @click="inboundPeriod = inboundPeriod === 'daily' ? 'monthly' : 'daily'; fetchInboundReport()">
              {{ inboundPeriod === 'daily' ? '切换月报' : '切换日报' }}
            </van-button>
          </template>
        </van-cell>
      </van-cell-group>

      <!-- 汇总数值卡片 -->
      <div v-if="inboundSummary" class="summary-cards">
        <div class="summary-card">
          <span class="sc-val">{{ inboundSummary.total_inbounds }}</span>
          <span class="sc-label">入库笔数</span>
        </div>
        <div class="summary-card highlight">
          <span class="sc-val">{{ inboundSummary.total_quantity }}</span>
          <span class="sc-label">入库总量</span>
        </div>
      </div>

      <!-- 移动端：卡片列表 -->
      <div v-if="!isPC && inboundData.length > 0">
        <van-cell v-for="r in inboundData" :key="r.date || `${r.year}-${r.month}`"
          :title="r.date || `${r.year}-${String(r.month).padStart(2,'0')}`"
          :label="`${r.inbound_count}笔 | 入库 ${r.total_quantity} 件`"
          value="" />
      </div>
      <!-- PC 端：DataTable -->
      <DataTable v-if="isPC" :columns="inboundColumns" :data="inboundData" :loading="inboundLoading"
        empty-text="暂无入库数据" />
      <van-empty v-if="!inboundLoading && inboundData.length === 0" description="暂无入库数据" />
    </template>

    <!-- ==================== 排行（销售→热销TOP，入库→库存TOP） ==================== -->
    <van-cell-group style="margin-top:8px">
      <van-cell :title="rankTitle + rankLimit">
        <template #right-icon>
          <van-stepper v-model="rankLimit" min="5" max="30" step="5" @change="fetchRank" />
        </template>
      </van-cell>
    </van-cell-group>

    <!-- 移动端排行 -->
    <div v-if="!isPC && rankData.length > 0">
      <van-cell v-for="r in rankData" :key="r.product_id"
        :title="r.product_name"
        :label="reportType === 'sales' ? `销量: ${r.total_quantity}` : `当前库存: ${r.current_stock}`"
        :value="reportType === 'sales' ? '¥' + r.total_amount : ''" />
    </div>
    <!-- PC 端排行 -->
    <DataTable v-if="isPC" :columns="rankColumns" :data="rankData" :loading="rankLoading"
      :empty-text="reportType === 'sales' ? '暂无销售数据' : '暂无库存数据'" />
    <van-empty v-if="!rankLoading && rankData.length === 0"
      :description="reportType === 'sales' ? '暂无热销数据' : '暂无库存数据'" />

    <!-- ==================== 数据截止时间 ==================== -->
    <div class="data-cutoff">
      数据可能有延迟，供参考
    </div>
  </div>
</template>

<style scoped>
.summary-cards {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
}
.summary-card {
  flex: 1;
  text-align: center;
  background: #fff;
  border-radius: 8px;
  padding: 12px 8px;
}
.summary-card.highlight {
  background: #ff6b81;
}
.summary-card.highlight .sc-val,
.summary-card.highlight .sc-label {
  color: #fff;
}
.sc-val {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: #323233;
}
.sc-label {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}
.data-cutoff {
  text-align: center;
  color: #999;
  font-size: 12px;
  padding: 24px 16px 40px;
}
</style>
