<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { useLayout } from '../composables/useLayout'

const API = '/api/v1'
const { isPC } = useLayout()

// ==================== 接口定义 ====================

interface MemberItem {
  id: number; name: string; phone: string; gender: string; birthday: string
  skin_type: string; tags: string; total_spent: number; points: number
  brand_points: Record<string, number>; remark: string
  created_at: string; updated_at: string
}

interface OrderItem {
  id: number; total_amount: number; actual_amount: number; discount: number
  items: { product_name: string; quantity: number; unit_price: number }[]
  created_at: string
}

// ==================== 响应式数据 ====================

const items = ref<MemberItem[]>([])
const keyword = ref('')
const page = ref(1)
const loading = ref(false)
const refreshing = ref(false)
const total = ref(0)

// 标签筛选
const activeTag = ref('')
const availableTags = ref<string[]>([])

// 积分品牌列表
const pointBrands = ref<string[]>(['赫莲娜', '娇兰'])

// 批量多选
const selectedIds = ref<Set<number>>(new Set())

const selectedCount = computed(() => selectedIds.value.size)
const allSelected = computed(() => {
  return items.value.length > 0 && items.value.every(m => selectedIds.value.has(m.id))
})
const anySelected = computed(() => selectedIds.value.size > 0)

// 表单弹窗
const showForm = ref(false)
const formTitle = ref('新增会员')
const editingId = ref<number | null>(null)
const form = ref({ name: '', phone: '', gender: '', birthday: '', skin_type: '', tags: '', remark: '' })

// 详情弹窗
const showDetail = ref(false)
const detailMember = ref<MemberItem | null>(null)
const detailOrders = ref<OrderItem[]>([])

// 积分调整弹窗
const showPointAdjust = ref(false)
const pointAdjustBrand = ref('赫莲娜')
const pointAdjustAmount = ref(0)
const pointAdjustRemark = ref('')
const pointAdjustMemberId = ref(0)

// 批量下发积分弹窗
const showBatchPoints = ref(false)
const batchPointsBrand = ref('赫莲娜')
const batchPointsAmount = ref(0)
const batchPointsRemark = ref('')

// 批量下发兑换券弹窗
const showBatchCoupons = ref(false)
const batchCouponBrand = ref('赫莲娜')
const batchCouponName = ref('')
const batchCouponExpiresAt = ref('')
const batchCouponRemark = ref('')

const skinTypeOptions = ['', '干性', '油性', '混合', '敏感']
const phonePattern = /^1[3-9]\d{9}$/

// ==================== 多选操作 ====================

function toggleSelect(id: number) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  selectedIds.value = next
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(items.value.map(m => m.id))
  }
}

function clearSelection() {
  selectedIds.value = new Set()
}

// ==================== API 调用 ====================

async function fetchMembers(showRefresh = false) {
  loading.value = true
  if (showRefresh) refreshing.value = true
  try {
    const params = new URLSearchParams({ page: String(page.value), page_size: '20' })
    if (keyword.value) params.set('keyword', keyword.value)
    if (activeTag.value) params.set('tags', activeTag.value)
    const res = await fetch(`${API}/members?${params}`)
    const data = await res.json()
    items.value = data.items
    total.value = data.total
    collectTags(data.items)
    clearSelection()
  } catch {
    /* ignore */
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
    if (activeTag.value) params.set('tags', activeTag.value)
    const res = await fetch(`${API}/members?${params}`)
    const data = await res.json()
    items.value = [...items.value, ...data.items]
    total.value = data.total
  } catch { /* ignore */ }
  loading.value = false
}

function collectTags(list: MemberItem[]) {
  const tagSet = new Set(availableTags.value)
  for (const m of list) {
    if (m.tags) {
      m.tags.split(',').forEach(t => { if (t.trim()) tagSet.add(t.trim()) })
    }
  }
  for (const m of list) {
    if (m.brand_points) {
      Object.keys(m.brand_points).forEach(b => {
        if (b && !pointBrands.value.includes(b)) {
          pointBrands.value.push(b)
        }
      })
    }
  }
  availableTags.value = Array.from(tagSet).sort()
}

function onSearch() { page.value = 1; fetchMembers() }
function onRefresh() { page.value = 1; fetchMembers(true) }
function onTagClick(tag: string) {
  activeTag.value = activeTag.value === tag ? '' : tag
  page.value = 1
  fetchMembers()
}

// ==================== 表单操作 ====================

function openCreate() {
  formTitle.value = '新增会员'
  editingId.value = null
  form.value = { name: '', phone: '', gender: '', birthday: '', skin_type: '', tags: '', remark: '' }
  showForm.value = true
}

function openEdit(m: MemberItem) {
  formTitle.value = '编辑会员'
  editingId.value = m.id
  form.value = {
    name: m.name, phone: m.phone, gender: m.gender || '',
    birthday: m.birthday || '', skin_type: m.skin_type || '',
    tags: m.tags || '', remark: m.remark || '',
  }
  showForm.value = true
}

async function submitForm() {
  if (!form.value.name.trim()) { showToast('请输入姓名'); return }
  if (!form.value.phone.trim()) { showToast('请输入手机号'); return }
  if (!phonePattern.test(form.value.phone)) { showToast('手机号格式不正确'); return }

  const url = editingId.value
    ? `${API}/members/${editingId.value}`
    : `${API}/members`
  const method = editingId.value ? 'PUT' : 'POST'
  const body: any = { ...form.value, phone: form.value.phone.trim(), name: form.value.name.trim() }
  if (!body.gender) delete body.gender
  if (!body.birthday) delete body.birthday
  if (!body.skin_type) delete body.skin_type
  if (!body.tags) body.tags = ''
  if (!body.remark) body.remark = ''

  try {
    const res = await fetch(url, {
      method, headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const err = await res.json()
      showToast(err.detail || '操作失败')
      return
    }
    showSuccessToast(editingId.value ? '更新成功' : '创建成功')
    showForm.value = false
    fetchMembers()
  } catch {
    showToast('网络错误')
  }
}

// ==================== 详情操作 ====================

async function openDetail(m: MemberItem) {
  try {
    const res = await fetch(`${API}/members/${m.id}`)
    const data = await res.json()
    detailMember.value = data
    detailOrders.value = data.orders || []
    showDetail.value = true
  } catch {
    showToast('获取详情失败')
  }
}

function openPointAdjust(memberId: number) {
  pointAdjustMemberId.value = memberId
  pointAdjustBrand.value = '赫莲娜'
  pointAdjustAmount.value = 0
  pointAdjustRemark.value = ''
  showDetail.value = false
  nextTick(() => { showPointAdjust.value = true })
}

async function submitPointAdjust() {
  if (!pointAdjustAmount.value) { showToast('请输入积分变化量'); return }
  try {
    const res = await fetch(`${API}/members/${pointAdjustMemberId.value}/points`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        amount: pointAdjustAmount.value,
        brand: pointAdjustBrand.value,
        remark: pointAdjustRemark.value || null,
      }),
    })
    if (!res.ok) { const err = await res.json(); showToast(err.detail || '操作失败'); return }
    showSuccessToast(`积分调整成功`)
    showPointAdjust.value = false
    fetchMembers()
  } catch { showToast('网络错误') }
}

function getBrandPoints(member: MemberItem | null, brand: string): number {
  if (!member || !member.brand_points) return 0
  return member.brand_points[brand] || 0
}

// ==================== 批量下发积分 ====================

function openBatchPoints() {
  if (selectedIds.value.size === 0) { showToast('请先勾选会员'); return }
  batchPointsBrand.value = '赫莲娜'
  batchPointsAmount.value = 0
  batchPointsRemark.value = ''
  showBatchPoints.value = true
}

async function submitBatchPoints() {
  if (!batchPointsAmount.value) { showToast('请输入积分数量'); return }
  try {
    const res = await fetch(`${API}/members/batch-points`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        member_ids: Array.from(selectedIds.value),
        brand: batchPointsBrand.value,
        amount: batchPointsAmount.value,
        remark: batchPointsRemark.value || null,
      }),
    })
    if (!res.ok) { const err = await res.json(); showToast(err.detail || '操作失败'); return }
    const data = await res.json()
    showSuccessToast(data.message)
    showBatchPoints.value = false
    clearSelection()
    fetchMembers()
  } catch { showToast('网络错误') }
}

// ==================== 批量下发兑换券 ====================

function openBatchCoupons() {
  if (selectedIds.value.size === 0) { showToast('请先勾选会员'); return }
  batchCouponBrand.value = '赫莲娜'
  batchCouponName.value = ''
  batchCouponExpiresAt.value = ''
  batchCouponRemark.value = ''
  showBatchCoupons.value = true
}

async function submitBatchCoupons() {
  if (!batchCouponName.value.trim()) { showToast('请输入兑换券名称'); return }
  if (!batchCouponExpiresAt.value) { showToast('请设置过期日期'); return }
  try {
    const res = await fetch(`${API}/members/batch-coupons`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        member_ids: Array.from(selectedIds.value),
        brand: batchCouponBrand.value,
        coupon_name: batchCouponName.value.trim(),
        expires_at: batchCouponExpiresAt.value,
        remark: batchCouponRemark.value || null,
      }),
    })
    if (!res.ok) { const err = await res.json(); showToast(err.detail || '操作失败'); return }
    const data = await res.json()
    showSuccessToast(data.message)
    showBatchCoupons.value = false
    clearSelection()
  } catch { showToast('网络错误') }
}

onMounted(() => { fetchMembers() })
</script>

<template>
  <div class="member-page">
    <!-- 顶部搜索栏 -->
    <div class="search-bar">
      <div class="search-input-wrap">
        <van-search v-model="keyword" shape="round" placeholder="搜索姓名 / 手机号" @search="onSearch" class="v-search" />
      </div>
      <van-button type="primary" size="small" @click="openCreate" class="add-btn">新增会员</van-button>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="isPC && anySelected" class="batch-bar">
      <span class="batch-info">已选 <strong>{{ selectedCount }}</strong> 个会员</span>
      <div class="batch-actions">
        <van-button type="warning" size="small" @click="openBatchPoints">批量下发积分</van-button>
        <van-button type="primary" size="small" @click="openBatchCoupons">批量下发兑换券</van-button>
        <van-button plain size="small" @click="clearSelection">取消选择</van-button>
      </div>
    </div>

    <!-- 标签筛选 -->
    <div v-if="availableTags.length > 0" class="filter-bar">
      <span
        class="filter-tag"
        :class="{ active: !activeTag }"
        @click="onTagClick('')"
      >全部</span>
      <span v-for="tag in availableTags" :key="tag"
        class="filter-tag"
        :class="{ active: activeTag === tag }"
        @click="onTagClick(tag)"
      >{{ tag }}</span>
    </div>

    <!-- 数据表格 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh" success-text="刷新成功">
      <van-list v-model:loading="loading" :finished="items.length >= total" finished-text="没有更多了" @load="onLoadMore">

        <!-- PC 表格视图 -->
        <div v-if="isPC" class="data-table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width:36px">
                  <input type="checkbox" :checked="allSelected" @change="toggleSelectAll" class="row-checkbox" />
                </th>
                <th style="width:44px">#</th>
                <th style="width:80px">姓名</th>
                <th style="width:120px">手机号</th>
                <th style="width:100px">标签</th>
                <th style="width:88px">累计消费</th>
                <th v-for="b in pointBrands" :key="b" style="width:88px">{{ b }}积分</th>
                <th style="width:80px">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(m, idx) in items" :key="m.id" class="clickable-row" :class="{ 'row-selected': selectedIds.has(m.id) }">
                <td @click.stop>
                  <input type="checkbox" :checked="selectedIds.has(m.id)" @change="toggleSelect(m.id)" class="row-checkbox" />
                </td>
                <td @click="openDetail(m)">{{ (page - 1) * 20 + idx + 1 }}</td>
                <td @click="openDetail(m)"><span class="cell-name">{{ m.name }}</span></td>
                <td @click="openDetail(m)">{{ m.phone }}</td>
                <td @click="openDetail(m)">
                  <span class="cell-name" style="color:#888;font-size:12px">{{ m.tags || '-' }}</span>
                </td>
                <td @click="openDetail(m)" class="num-cell">￥{{ m.total_spent?.toLocaleString?.() || m.total_spent || 0 }}</td>
                <td v-for="b in pointBrands" :key="b" class="num-cell" @click="openDetail(m)">
                  {{ getBrandPoints(m, b) }}
                </td>
                <td>
                  <van-button type="primary" size="mini" @click.stop="openEdit(m)">编辑</van-button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 移动端列表视图 -->
        <template v-else>
          <van-cell v-for="(m, idx) in items" :key="m.id"
            :title="`${idx + 1}. ${m.name}`"
            :label="`${m.phone} · 累计消费 ￥${m.total_spent || 0}`" center
            is-link @click="openDetail(m)">
            <template #icon v-if="m.tags">
              <van-tag type="primary" size="medium" style="margin-right:8px" v-for="t in m.tags.split(',').filter(Boolean)" :key="t">{{ t }}</van-tag>
            </template>
          </van-cell>
        </template>

      </van-list>
    </van-pull-refresh>

    <!-- ==================== 新增/编辑弹窗 ==================== -->
    <van-popup v-model:show="showForm" position="bottom" round :style="{ height: '80vh', maxWidth: '480px', margin: '0 auto' }">
      <div style="padding:20px;overflow-y:auto;height:100%">
        <h3 style="margin:0 0 16px;font-size:18px">{{ formTitle }}</h3>

        <van-field v-model="form.name" label="姓名 *" placeholder="请输入姓名" maxlength="20" />
        <van-field v-model="form.phone" label="手机号 *" placeholder="请输入手机号" maxlength="11" type="tel" />
        <van-field v-model="form.birthday" label="生日" placeholder="如 1990-01-01" maxlength="10" />
        <van-field v-model="form.tags" label="标签" placeholder="多个标签用逗号分隔" maxlength="100" />

        <div style="margin:12px 16px">
          <div style="font-size:14px;color:#646566;margin-bottom:8px">性别</div>
          <van-radio-group v-model="form.gender" direction="horizontal">
            <van-radio name="男">男</van-radio>
            <van-radio name="女">女</van-radio>
            <van-radio name="">未知</van-radio>
          </van-radio-group>
        </div>

        <div style="margin:12px 16px">
          <div style="font-size:14px;color:#646566;margin-bottom:8px">肤质</div>
          <van-radio-group v-model="form.skin_type" direction="horizontal">
            <van-radio name="" style="margin-right:8px">不限</van-radio>
            <van-radio v-for="s in skinTypeOptions.filter(Boolean)" :key="s" :name="s" style="margin-right:8px">{{ s }}</van-radio>
          </van-radio-group>
        </div>

        <van-field v-model="form.remark" label="备注" placeholder="可选" rows="2" type="textarea" />

        <div style="display:flex;gap:12px;margin-top:20px">
          <van-button plain @click="showForm = false" style="flex:1">取消</van-button>
          <van-button type="primary" @click="submitForm" style="flex:1">保存</van-button>
        </div>
      </div>
    </van-popup>

    <!-- ==================== 详情弹窗 ==================== -->
    <van-popup v-model:show="showDetail" position="bottom" round :style="{ height: '80vh', maxWidth: '480px', margin: '0 auto' }">
      <div v-if="detailMember" style="padding:20px;overflow-y:auto;height:100%">
        <h3 style="margin:0 0 16px;font-size:18px">{{ detailMember.name }} 的详情</h3>

        <van-cell-group inset style="margin-bottom:12px">
          <van-cell title="手机号" :value="detailMember.phone" />
          <van-cell title="性别" :value="detailMember.gender || '未知'" />
          <van-cell title="生日" :value="detailMember.birthday || '-'" />
          <van-cell title="肤质" :value="detailMember.skin_type || '-'" />
          <van-cell title="注册时间" :value="detailMember.created_at?.slice(0, 10) || '-'" />
          <van-cell title="标签" :value="detailMember.tags || '-'" />
          <van-cell title="累计消费" :value="'￥' + (detailMember.total_spent || 0)" />
        </van-cell-group>

        <!-- 品牌积分明细 -->
        <van-cell-group inset style="margin-bottom:12px" title="积分明细">
          <van-cell v-for="b in pointBrands" :key="b" :title="b + '积分'" :value="String(getBrandPoints(detailMember, b))" />
        </van-cell-group>

        <van-button type="warning" block @click="openPointAdjust(detailMember.id)" style="margin-bottom:12px">积分调整</van-button>

        <!-- 消费记录 -->
        <h4 style="margin:16px 0 8px;font-size:15px">消费记录（近50笔）</h4>
        <div v-if="detailOrders.length === 0" style="color:#999;font-size:13px;text-align:center;padding:20px">暂无消费记录</div>
        <div v-for="o in detailOrders" :key="o.id" style="font-size:13px;padding:10px;border-bottom:1px solid #f0f0f0">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span style="font-weight:600">￥{{ o.actual_amount }}</span>
            <span style="color:#999">{{ o.created_at?.slice(0, 10) }}</span>
          </div>
          <div v-for="(item, iidx) in o.items" :key="iidx" style="color:#666;font-size:12px">
            {{ item.product_name }} x{{ item.quantity }} (￥{{ item.unit_price }})
          </div>
        </div>

        <div style="display:flex;gap:12px;margin-top:20px">
          <van-button plain @click="showDetail = false" style="flex:1">关闭</van-button>
          <van-button type="primary" @click="showDetail = false; openEdit(detailMember)" style="flex:1">编辑</van-button>
        </div>
      </div>
    </van-popup>

    <!-- ==================== 积分调整弹窗 ==================== -->
    <van-popup v-model:show="showPointAdjust" position="bottom" round :style="{ maxWidth: '480px', margin: '0 auto' }">
      <div style="padding:20px">
        <h3 style="margin:0 0 16px;font-size:18px">积分调整</h3>

        <van-field label="品牌">
          <template #input>
            <van-radio-group v-model="pointAdjustBrand" direction="horizontal">
              <van-radio v-for="b in pointBrands" :key="b" :name="b" style="margin-right:12px">{{ b }}</van-radio>
            </van-radio-group>
          </template>
        </van-field>

        <van-field v-model.number="pointAdjustAmount" label="变化量" type="digit" placeholder="正数增加，负数扣减" />
        <van-field v-model="pointAdjustRemark" label="备注" placeholder="可选" />

        <div style="display:flex;gap:12px;margin-top:20px">
          <van-button plain @click="showPointAdjust = false" style="flex:1">取消</van-button>
          <van-button type="primary" @click="submitPointAdjust" style="flex:1">确认调整</van-button>
        </div>
      </div>
    </van-popup>

    <!-- ==================== 批量下发积分弹窗 ==================== -->
    <van-popup v-model:show="showBatchPoints" position="bottom" round :style="{ maxWidth: '480px', margin: '0 auto' }">
      <div style="padding:20px">
        <h3 style="margin:0 0 16px;font-size:18px">批量下发积分</h3>
        <p style="margin:0 0 12px;color:#888;font-size:13px">将为已选的 {{ selectedCount }} 个会员统一发放积分</p>

        <van-field label="品牌">
          <template #input>
            <van-radio-group v-model="batchPointsBrand" direction="horizontal">
              <van-radio v-for="b in pointBrands" :key="b" :name="b" style="margin-right:12px">{{ b }}</van-radio>
            </van-radio-group>
          </template>
        </van-field>

        <van-field v-model.number="batchPointsAmount" label="积分数量 *" type="digit" placeholder="正数增加，负数扣减" />
        <van-field v-model="batchPointsRemark" label="备注" placeholder="可选，如：春节活动赠送" />

        <div style="display:flex;gap:12px;margin-top:20px">
          <van-button plain @click="showBatchPoints = false" style="flex:1">取消</van-button>
          <van-button type="warning" @click="submitBatchPoints" style="flex:1">确认下发</van-button>
        </div>
      </div>
    </van-popup>

    <!-- ==================== 批量下发兑换券弹窗 ==================== -->
    <van-popup v-model:show="showBatchCoupons" position="bottom" round :style="{ maxWidth: '480px', margin: '0 auto' }">
      <div style="padding:20px">
        <h3 style="margin:0 0 16px;font-size:18px">批量下发兑换券</h3>
        <p style="margin:0 0 12px;color:#888;font-size:13px">将为已选的 {{ selectedCount }} 个会员每人发一张兑换券</p>

        <van-field label="品牌">
          <template #input>
            <van-radio-group v-model="batchCouponBrand" direction="horizontal">
              <van-radio v-for="b in pointBrands" :key="b" :name="b" style="margin-right:12px">{{ b }}</van-radio>
            </van-radio-group>
          </template>
        </van-field>

        <van-field v-model="batchCouponName" label="券名称 *" placeholder="如：黑绷带50ml兑换券" maxlength="50" />
        <van-field v-model="batchCouponExpiresAt" label="过期日期 *" placeholder="2026-12-31" maxlength="10" />
        <van-field v-model="batchCouponRemark" label="备注" placeholder="可选" />

        <div style="display:flex;gap:12px;margin-top:20px">
          <van-button plain @click="showBatchCoupons = false" style="flex:1">取消</van-button>
          <van-button type="primary" @click="submitBatchCoupons" style="flex:1">确认下发</van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.member-page {
  padding-bottom: env(safe-area-inset-bottom, 16px);
}

/* 搜索栏 */
.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #fff;
}
.search-input-wrap { flex: 1; }
.search-input-wrap :deep(.van-search) { padding: 0; }
.search-input-wrap :deep(.van-search__content) { background: #f5f5f5; }
.add-btn { flex-shrink: 0; }

/* 批量操作栏 */
.batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #fff7e6;
  border-bottom: 1px solid #ffd666;
}
.batch-info {
  font-size: 13px;
  color: #ad6800;
}
.batch-info strong {
  font-size: 15px;
}
.batch-actions {
  display: flex;
  gap: 8px;
}

/* 标签筛选 */
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
  padding: 0 16px;
}
.data-table {
  width: 100%;
  min-width: 780px;
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
.cell-name {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.data-table tbody tr:nth-child(even) { background: #fafbfc; }
.data-table tbody tr:hover { background: #edf4ff; }
.clickable-row { cursor: pointer; }
.row-selected { background: #fff7e6 !important; }
.num-cell {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* 复选框 */
.row-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #ff6b81;
}
</style>
