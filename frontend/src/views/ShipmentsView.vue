<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { useLayout } from '../composables/useLayout'

const API = '/api/v1'

interface Shipment {
  id: number
  sale_order_id: number
  order_number: string | null
  express_company: string | null
  express_no: string | null
  ship_status: string
  receiver_name: string | null
  receiver_phone: string | null
  receiver_address: string | null
  remark: string | null
  created_at: string | null
}

const shipments = ref<Shipment[]>([])
const loading = ref(false)
const showForm = ref(false)
const showDetail = ref(false)
const activeTab = ref('pending')
const detailShipment = ref<Shipment | null>(null)

const form = ref({
  sale_order_id: 0,
  express_company: '顺丰',
  express_no: '',
  receiver_name: '',
  receiver_phone: '',
  receiver_address: '',
  remark: '',
})

const expressCompanies = ['顺丰', '中通', '圆通', '韵达', '邮政', '其他']
const statusColor: Record<string, string> = {
  '未发货': '#ff976a',
  '已发货': '#1989fa',
  '已签收': '#07c160',
  '已退货': '#999',
}

const filterStatus = computed(() => activeTab.value === 'all' ? '' : '未发货')

async function fetchShipments() {
  loading.value = true
  try {
    const params = new URLSearchParams({ page_size: '100' })
    if (filterStatus.value) params.set('ship_status', filterStatus.value)
    const res = await fetch(`${API}/shipments?${params}`)
    const data = await res.json()
    shipments.value = data.items || []
  } finally {
    loading.value = false
  }
}

async function updateStatus(shipment: Shipment, newStatus: string) {
  const res = await fetch(`${API}/shipments/${shipment.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ship_status: newStatus }),
  })
  if (res.ok) {
    showSuccessToast(`状态更新: ${newStatus}`)
    fetchShipments()
  } else {
    showToast('更新失败')
  }
}

function openDetail(s: Shipment) {
  detailShipment.value = s
  showDetail.value = true
}

function showShipmentForm(s: Shipment) {
  detailShipment.value = s
  showDetail.value = false
  form.value = {
    sale_order_id: s.sale_order_id,
    express_company: '顺丰',
    express_no: '',
    receiver_name: '',
    receiver_phone: '',
    receiver_address: '',
    remark: '',
  }
  showForm.value = true
}

async function updateShipment() {
  const shipment = detailShipment.value
  if (!shipment) return
  const res = await fetch(`${API}/shipments/${shipment.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      express_company: form.value.express_company,
      express_no: form.value.express_no,
      receiver_name: form.value.receiver_name,
      receiver_phone: form.value.receiver_phone,
      receiver_address: form.value.receiver_address,
      remark: form.value.remark,
    }),
  })
  if (res.ok) {
    showSuccessToast('发货信息已更新')
    showForm.value = false
    fetchShipments()
  } else {
    showToast('更新失败')
  }
}

const { isPC } = useLayout()

onMounted(fetchShipments)
</script>

<template>
  <div class="page">
    <van-nav-bar title="发货管理" fixed placeholder />

    <!-- 状态筛选 tab -->
    <van-tabs v-model:active="activeTab" @change="fetchShipments" sticky :offset-top="46">
      <van-tab title="未发货" name="pending" />
      <van-tab title="全部" name="all" />
    </van-tabs>

    <van-pull-refresh v-model="loading" @refresh="fetchShipments">

      <!-- PC 表格视图 -->
      <div v-if="isPC" class="data-table-wrap" style="margin-top:8px">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width:44px">#</th>
              <th style="width:130px">单据编号</th>
              <th style="width:72px">快递公司</th>
              <th style="width:150px">快递单号</th>
              <th style="width:72px">收货人</th>
              <th style="width:120px">收货电话</th>
              <th style="width:72px">状态</th>
              <th style="width:130px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(s, idx) in shipments" :key="s.id">
              <td>{{ idx + 1 }}</td>
              <td>
                <span style="font-weight:bold;color:#1989fa;cursor:pointer" @click="openDetail(s)">
                  {{ s.order_number || `#${s.sale_order_id}` }}
                </span>
              </td>
              <td>{{ s.express_company || '-' }}</td>
              <td><code>{{ s.express_no || '-' }}</code></td>
              <td>{{ s.receiver_name || '-' }}</td>
              <td>{{ s.receiver_phone || '-' }}</td>
              <td><van-tag :color="statusColor[s.ship_status] || '#999'" size="medium">{{ s.ship_status }}</van-tag></td>
              <td>
                <div style="display:flex;gap:8px">
                  <van-button v-if="s.ship_status === '未发货'" size="small" type="primary" plain
                    @click="showShipmentForm(s)">
                    录入快递
                  </van-button>
                  <van-button v-if="s.ship_status === '未发货'" size="small" type="success" plain
                    @click="updateStatus(s, '已发货')">
                    标记发货
                  </van-button>
                  <van-button v-if="s.ship_status === '已发货'" size="small" type="success" plain
                    @click="updateStatus(s, '已签收')">
                    标记签收
                  </van-button>
                  <span v-if="s.ship_status === '已签收' || s.ship_status === '已退货'" style="color:#999;font-size:12px">--</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="shipments.length === 0" style="text-align:center;padding:40px;color:#999">
          暂无{{ activeTab === 'pending' ? '未发货' : '' }}记录
        </div>
      </div>

      <!-- 移动端列表视图 -->
      <template v-else>
        <div v-if="shipments.length === 0" style="text-align:center;padding:40px 16px;color:#999">
          暂无{{ activeTab === 'pending' ? '未发货' : '' }}记录
        </div>
        <van-cell v-for="s in shipments" :key="s.id"
          :title="s.order_number || `销售单 #${s.sale_order_id}`"
          :label="`${s.express_company || '未录入'} | ${s.express_no || '-'} | ${s.receiver_name || '-'} ${s.receiver_phone || ''}`"
          @click="openDetail(s)" is-link>
          <template #value>
            <van-tag :color="statusColor[s.ship_status] || '#999'">{{ s.ship_status }}</van-tag>
          </template>
        </van-cell>
      </template>
    </van-pull-refresh>

    <!-- 详情弹窗 -->
    <van-popup v-model:show="showDetail" position="bottom" :style="{ height: '50%' }" round>
      <van-nav-bar title="发货详情" left-text="关闭" @click-left="showDetail = false" />
      <div v-if="detailShipment" style="padding:16px">
        <van-cell-group inset>
          <van-cell title="单据编号" :value="detailShipment.order_number || `#${detailShipment.sale_order_id}`" />
          <van-cell title="快递公司" :value="detailShipment.express_company || '未录入'" />
          <van-cell title="快递单号" :value="detailShipment.express_no || '未录入'" />
          <van-cell title="收货人" :value="detailShipment.receiver_name || '-'" />
          <van-cell title="收货电话" :value="detailShipment.receiver_phone || '-'" />
          <van-cell title="收货地址" :value="detailShipment.receiver_address || '-'" />
          <van-cell title="备注" :value="detailShipment.remark || '-'" />
          <van-cell title="状态">
            <template #value>
              <van-tag :color="statusColor[detailShipment.ship_status] || '#999'">{{ detailShipment.ship_status }}</van-tag>
            </template>
          </van-cell>
        </van-cell-group>

        <div v-if="detailShipment.ship_status === '未发货'" style="margin-top:16px;display:flex;gap:12px">
          <van-button type="primary" block @click="showShipmentForm(detailShipment)">录入快递信息</van-button>
          <van-button type="success" block @click="updateStatus(detailShipment, '已发货'); showDetail = false">
            直接标记发货
          </van-button>
        </div>
        <div v-if="detailShipment.ship_status === '已发货'" style="margin-top:16px">
          <van-button type="success" block @click="updateStatus(detailShipment, '已签收'); showDetail = false">
            标记已签收
          </van-button>
        </div>
      </div>
    </van-popup>

    <!-- 录入快递弹窗 -->
    <van-popup v-model:show="showForm" position="bottom" :style="{ height: '65%' }" round>
      <van-nav-bar title="录入快递信息" left-text="取消" @click-left="showForm = false" />
      <van-form @submit="updateShipment" style="padding:16px">
        <van-field name="express_company" label="快递公司">
          <template #input>
            <van-radio-group v-model="form.express_company" direction="horizontal">
              <van-radio v-for="e in expressCompanies" :key="e" :name="e" style="margin:4px 6px;font-size:13px">{{ e }}</van-radio>
            </van-radio-group>
          </template>
        </van-field>
        <van-field v-model="form.express_no" label="快递单号" placeholder="请输入快递单号" />
        <van-field v-model="form.receiver_name" label="收货人" placeholder="选填" />
        <van-field v-model="form.receiver_phone" label="收货电话" placeholder="选填" />
        <van-field v-model="form.receiver_address" label="收货地址" placeholder="选填" type="textarea" rows="2" />
        <van-field v-model="form.remark" label="备注" placeholder="选填" />
        <van-button type="primary" block native-type="submit" style="margin-top:16px">保存</van-button>
      </van-form>
    </van-popup>
  </div>
</template>

<style scoped>
.data-table-wrap {
  overflow-x: auto;
  padding: 0 16px;
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
.data-table code {
  font-size: 12px;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  letter-spacing: 0.5px;
}
</style>
