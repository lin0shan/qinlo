<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { useLayout } from '../composables/useLayout'

const API = '/api/v1'
const { isPC } = useLayout()

interface CouponItem {
  id: number; member_id: number; member_name: string; member_phone: string
  brand: string; coupon_name: string; product_name: string | null
  status: string; expires_at: string | null; used_at: string | null
  remark: string | null; created_at: string | null
}

const items = ref<CouponItem[]>([])
const page = ref(1)
const total = ref(0)
const loading = ref(false)
const refreshing = ref(false)

const filterBrand = ref('')
const filterStatus = ref('有效')

const statusOptions = ['有效', '已兑换', '已过期']

function daysUntil(dateStr: string | null): number {
  if (!dateStr) return 0
  const d = new Date(dateStr.slice(0, 10))
  return Math.ceil((d.getTime() - Date.now()) / 86400000)
}

function isExpired(dateStr: string | null): boolean {
  return daysUntil(dateStr) < 0
}

function isExpiringSoon(dateStr: string | null): boolean {
  const d = daysUntil(dateStr)
  return d >= 0 && d <= 30
}

async function fetchCoupons(showRefresh = false) {
  loading.value = true
  if (showRefresh) refreshing.value = true
  try {
    const params = new URLSearchParams({ page: String(page.value), page_size: '50' })
    if (filterBrand.value) params.set('brand', filterBrand.value)
    if (filterStatus.value) params.set('status', filterStatus.value)
    const res = await fetch(`${API}/coupons?${params}`)
    const data = await res.json()
    items.value = data.items
    total.value = data.total
  } catch { /* ignore */ }
  loading.value = false
  refreshing.value = false
}

async function onLoadMore() {
  if (items.value.length >= total.value) return
  page.value++
  loading.value = true
  try {
    const params = new URLSearchParams({ page: String(page.value), page_size: '50', brand: filterBrand.value, status: filterStatus.value })
    const res = await fetch(`${API}/coupons?${params}`)
    const data = await res.json()
    items.value = [...items.value, ...data.items]
  } catch { /* ignore */ }
  loading.value = false
}

function onFilter() { page.value = 1; fetchCoupons() }
function onRefresh() { page.value = 1; fetchCoupons(true) }

async function markUsed(coupon: CouponItem) {
  try {
    const res = await fetch(`${API}/coupons/${coupon.id}/status?status=已兑换`, { method: 'PUT' })
    if (!res.ok) { const err = await res.json(); showToast(err.detail || '操作失败'); return }
    showSuccessToast('已标记为已兑换')
    fetchCoupons()
  } catch { showToast('网络错误') }
}

onMounted(() => { fetchCoupons() })
</script>

<template>
  <div class="coupon-page">
    <!-- 标题 -->
    <div class="search-bar">
      <h3 style="margin:0">兑换券管理</h3>
    </div>

    <!-- 筛选 -->
    <div class="filter-row">
      <div class="filter-group">
        <span class="filter-label">品牌：</span>
        <span class="filter-tag" :class="{ active: !filterBrand }" @click="filterBrand='';onFilter()">全部</span>
        <span class="filter-tag" :class="{ active: filterBrand==='赫莲娜' }" @click="filterBrand='赫莲娜';onFilter()">赫莲娜</span>
        <span class="filter-tag" :class="{ active: filterBrand==='娇兰' }" @click="filterBrand='娇兰';onFilter()">娇兰</span>
      </div>
      <div class="filter-group">
        <span class="filter-label">状态：</span>
        <span class="filter-tag" :class="{ active: !filterStatus }" @click="filterStatus='';onFilter()">全部</span>
        <span v-for="s in statusOptions" :key="s" class="filter-tag" :class="{ active: filterStatus===s }" @click="filterStatus=s;onFilter()">{{ s }}</span>
      </div>
    </div>

    <!-- 数据表格 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh" success-text="刷新成功">
      <van-list v-model:loading="loading" :finished="items.length >= total" finished-text="没有更多了" @load="onLoadMore">

        <div v-if="isPC" class="data-table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width:3%">#</th>
                <th style="width:7%">会员</th>
                <th style="width:9%">手机号</th>
                <th style="width:5%">品牌</th>
                <th>兑换券</th>
                <th style="width:6%">状态</th>
                <th style="width:9%">过期日期</th>
                <th style="width:5%">剩余</th>
                <th style="width:7%">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(c, idx) in items" :key="c.id" :class="{ 'row-expired': c.status==='有效' && isExpired(c.expires_at) }">
                <td>{{ (page - 1) * 50 + idx + 1 }}</td>
                <td><span class="cell-name">{{ c.member_name || '-' }}</span></td>
                <td>{{ c.member_phone || '-' }}</td>
                <td>{{ c.brand }}</td>
                <td><span class="cell-name">{{ c.coupon_name }}</span></td>
                <td>
                  <span v-if="c.status==='有效' && isExpiringSoon(c.expires_at)" style="color:#ff976a;font-size:12px">即将到期</span>
                  <span v-else-if="c.status==='有效'" style="color:#07c160;font-size:12px">有效</span>
                  <span v-else-if="c.status==='已过期'" style="color:#999;font-size:12px">已过期</span>
                  <span v-else style="color:#1989fa;font-size:12px">已兑换</span>
                </td>
                <td><span class="cell-name" style="font-size:12px">{{ c.expires_at?.slice(0, 10) || '-' }}</span></td>
                <td>
                  <span v-if="c.status==='有效'" :style="{ color: isExpired(c.expires_at) ? '#ee0a24' : isExpiringSoon(c.expires_at) ? '#ff976a' : '#666' }">
                    {{ isExpired(c.expires_at) ? '已过期' : daysUntil(c.expires_at) + '天' }}
                  </span>
                  <span v-else>-</span>
                </td>
                <td>
                  <van-button v-if="c.status==='有效'" type="primary" size="mini" @click="markUsed(c)">兑换</van-button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 移动端列表 -->
        <template v-else>
          <van-cell v-for="(c, idx) in items" :key="c.id" :title="`${idx+1}. ${c.coupon_name}`" :label="`${c.member_name} · ${c.brand} · ${c.status} · 到期${c.expires_at?.slice(0,10) || '-'}`">
            <template #right-icon>
              <van-button v-if="c.status==='有效'" type="primary" size="small" @click.stop="markUsed(c)">兑换</van-button>
            </template>
          </van-cell>
        </template>

      </van-list>
    </van-pull-refresh>
  </div>
</template>

<style scoped>
.coupon-page { padding-bottom: env(safe-area-inset-bottom, 16px); }

.search-bar { display: flex; align-items: center; padding: 12px 16px 8px; background: #fff; }

.filter-row { display: flex; flex-wrap: wrap; gap: 12px; padding: 8px 16px; background: #fff; border-bottom: 1px solid #f0f0f0; }
.filter-group { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.filter-label { font-size: 13px; color: #888; }
.filter-tag { padding: 3px 10px; border-radius: 12px; font-size: 12px; color: #666; background: #f5f5f5; cursor: pointer; transition: all 0.15s; user-select: none; }
.filter-tag.active { color: #fff; background: #ff6b81; }
.filter-tag:hover { opacity: 0.8; }

.data-table-wrap { overflow-x: auto; }
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
.data-table th:first-child { border-left: none; }
.data-table td {
  padding: 10px 8px;
  border: 1px solid #e9e9e9;
  vertical-align: middle;
}
.data-table td:first-child { border-left: none; }
.data-table tbody tr:nth-child(even) { background: #fafbfc; }
.data-table tbody tr:hover { background: #edf4ff; }
.cell-name { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.row-expired { background: #fff5f5 !important; }
</style>
