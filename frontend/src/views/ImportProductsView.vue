<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { showNotify } from 'vant'

const API = '/api/v1'
const router = useRouter()

// Step: 1=upload, 2=preview, 3=result
const step = ref(1)
const loading = ref(false)

// 上传
const file = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

// Preview data
interface PreviewRow {
  row_number: number
  data: Record<string, any>
  errors: string[]
  valid: boolean
}
const previewRows = ref<PreviewRow[]>([])
const totalRows = ref(0)
const validCount = ref(0)
const invalidCount = ref(0)

// Import result
interface ImportResult {
  total: number
  success: number
  failed: Array<{ row_number: number; errors: string[] }>
}
const importResult = ref<ImportResult | null>(null)

// Column definitions
const COLUMN_LABELS: Record<string, string> = {
  name: '商品名称',
  brand: '品牌',
  category: '分类',
  spec: '规格',
  unit: '单位',
  barcode: '条码',
  sku_code: 'SKU编码',
  cost_price: '成本价',
  retail_price: '零售价',
  wholesale_price: '批发价',
  safety_stock: '安全库存',
  remark: '备注',
}
const columns = Object.keys(COLUMN_LABELS)
const showColumns = ref(columns.map(c => ({ key: c, label: COLUMN_LABELS[c], visible: true })))

// Responsive layout
const isPC = ref(window.innerWidth >= 1280)
window.addEventListener('resize', () => {
  isPC.value = window.innerWidth >= 1280
})

// Download template
async function downloadTemplate() {
  try {
    const res = await fetch(`${API}/import/products/template`)
    if (!res.ok) throw new Error('下载失败')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '商品导入模板.xlsx'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch {
    showNotify({ type: 'danger', message: '下载模板失败，请检查网络连接' })
  }
}

// File selection
function triggerFileInput() {
  fileInput.value?.click()
}
function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) {
    file.value = input.files[0]
  }
}
function removeFile() {
  file.value = null
  if (fileInput.value) fileInput.value.value = ''
}

// Upload preview
async function uploadPreview() {
  if (!file.value) return
  loading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    const res = await fetch(`${API}/import/products/preview`, {
      method: 'POST',
      body: fd,
    })
    if (!res.ok) throw new Error('解析失败')
    const data = await res.json()
    previewRows.value = data.rows
    totalRows.value = data.total_rows
    validCount.value = data.valid_count
    invalidCount.value = data.invalid_count
    step.value = 2
    if (data.total_rows === 0) {
      showNotify({ type: 'warning', message: data.message || '文件中未找到有效数据' })
    }
  } catch {
    showNotify({ type: 'danger', message: '文件解析失败，请检查文件格式是否正确' })
  } finally {
    loading.value = false
  }
}

// Confirm import
async function confirmImport() {
  if (!file.value) return
  loading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    const res = await fetch(`${API}/import/products/confirm`, {
      method: 'POST',
      body: fd,
    })
    if (!res.ok) throw new Error('导入失败')
    importResult.value = await res.json()
    step.value = 3
  } catch {
    showNotify({ type: 'danger', message: '导入失败，请重试' })
  } finally {
    loading.value = false
  }
}

// Back to step 1
function backToUpload() {
  step.value = 1
  previewRows.value = []
}

// Go to product list
function goToProducts() {
  router.push({ name: 'Products' })
}

// Start over
function restart() {
  step.value = 1
  file.value = null
  previewRows.value = []
  importResult.value = null
  if (fileInput.value) fileInput.value.value = ''
}

// Filename (truncated display)
const displayFileName = computed(() => {
  if (!file.value) return ''
  const name = file.value.name
  return name.length > 30 ? name.substring(0, 27) + '...' : name
})
</script>

<template>
  <div class="import-page">
    <div class="page-header">
      <h2>批量导入商品</h2>
      <van-button v-if="step === 3" size="small" @click="restart">导入新文件</van-button>
    </div>

    <!-- 步骤指示器 -->
    <van-steps :active="step - 1" class="steps-bar">
      <van-step>上传文件</van-step>
      <van-step>预览确认</van-step>
      <van-step>导入完成</van-step>
    </van-steps>

    <!-- Step 1: 上传 -->
    <div v-if="step === 1" class="step-content">
      <!-- 操作指南 -->
      <div class="guide-card">
        <h4>操作指南</h4>
        <ol>
          <li>点击下方按钮下载 <b>商品导入模板</b></li>
          <li>在 Excel 中按模板格式填入商品数据（<b>商品名称</b>为必填）</li>
          <li>条码和 SKU 编码可留空，系统将自动生成</li>
          <li>上传文件后预览校验，确认无误后一键导入</li>
        </ol>
      </div>

      <!-- 下载模板 -->
      <div class="action-row">
        <van-button
          icon="down"
          type="default"
          size="large"
          block
          @click="downloadTemplate"
        >
          下载导入模板
        </van-button>
      </div>

      <!-- 文件选择 -->
      <div class="upload-area" :class="{ 'has-file': file }">
        <input
          ref="fileInput"
          type="file"
          accept=".xlsx,.xls"
          style="display:none"
          @change="onFileChange"
        />

        <div v-if="!file" class="upload-placeholder" @click="triggerFileInput">
          <van-icon name="add-o" size="36" />
          <span>点击选择 Excel 文件</span>
          <span class="upload-hint">支持 .xlsx / .xls 格式</span>
        </div>

        <div v-else class="upload-file-info">
          <van-icon name="description" size="20" color="#1989fa" />
          <span class="file-name">{{ displayFileName }}</span>
          <van-icon name="clear" size="16" color="#999" class="remove-btn" @click="removeFile" />
        </div>
      </div>

      <!-- 上传按钮 -->
      <van-button
        type="primary"
        size="large"
        block
        :disabled="!file"
        :loading="loading"
        loading-text="解析中..."
        @click="uploadPreview"
      >
        {{ file ? '上传解析' : '请先选择文件' }}
      </van-button>
    </div>

    <!-- Step 2: 预览 -->
    <div v-if="step === 2" class="step-content">
      <!-- 汇总信息 -->
      <div class="preview-summary">
        <div class="summary-item">
          <span class="summary-num">{{ totalRows }}</span>
          <span class="summary-label">总行数</span>
        </div>
        <div class="summary-item valid">
          <span class="summary-num">{{ validCount }}</span>
          <span class="summary-label">校验通过</span>
        </div>
        <div class="summary-item invalid" v-if="invalidCount > 0">
          <span class="summary-num">{{ invalidCount }}</span>
          <span class="summary-label">存在问题</span>
        </div>
      </div>

      <div v-if="invalidCount > 0" class="warning-bar">
        <van-icon name="warning-o" />
        存在 {{ invalidCount }} 行数据校验未通过，仅通过校验的行会被导入
      </div>

      <!-- 预览表格 -->
      <div class="preview-table-wrap">
        <table class="preview-table" v-if="previewRows.length > 0">
          <thead>
            <tr>
              <th class="col-num">#</th>
              <th
                v-for="col in showColumns.filter(c => c.visible)"
                :key="col.key"
                :class="{ 'col-required': col.key === 'name' }"
              >
                {{ col.label }}{{ col.key === 'name' ? ' *' : '' }}
              </th>
              <th class="col-status">状态</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in previewRows"
              :key="row.row_number"
              :class="{ 'row-invalid': !row.valid }"
            >
              <td class="col-num">{{ row.row_number }}</td>
              <td
                v-for="col in showColumns.filter(c => c.visible)"
                :key="col.key"
              >
                {{ row.data[col.key] }}
              </td>
              <td class="col-status">
                <span v-if="row.valid" class="tag-ok">通过</span>
                <span v-else class="tag-err">
                  有误
                  <span class="error-tip">
                    <div v-for="err in row.errors" :key="err">{{ err }}</div>
                  </span>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <van-empty v-else description="无预览数据" />
      </div>

      <!-- 操作按钮 -->
      <div class="step-actions">
        <van-button @click="backToUpload" :disabled="loading">返回重选</van-button>
        <van-button
          type="primary"
          :loading="loading"
          loading-text="导入中..."
          :disabled="validCount === 0"
          @click="confirmImport"
        >
          确认导入 ({{ validCount }} 条)
        </van-button>
      </div>
    </div>

    <!-- Step 3: 结果 -->
    <div v-if="step === 3 && importResult" class="step-content">
      <div class="result-card" :class="{ 'all-success': importResult.failed.length === 0 }">
        <div class="result-icon">
          <van-icon
            :name="importResult.failed.length === 0 ? 'success' : 'warning-o'"
            :color="importResult.failed.length === 0 ? '#07c160' : '#ff976a'"
            size="48"
          />
        </div>
        <div class="result-title">
          {{ importResult.failed.length === 0 ? '全部导入成功' : '导入完成' }}
        </div>
        <div class="result-stats">
          <span>共 {{ importResult.total }} 条</span>
          <span class="stat-divider">|</span>
          <span class="stat-success">成功 {{ importResult.success }} 条</span>
          <span v-if="importResult.failed.length > 0" class="stat-divider">|</span>
          <span v-if="importResult.failed.length > 0" class="stat-fail">失败 {{ importResult.failed.length }} 条</span>
        </div>

        <!-- 失败详情 -->
        <div v-if="importResult.failed.length > 0" class="failed-list">
          <h4>失败详情</h4>
          <div v-for="item in importResult.failed" :key="item.row_number" class="failed-item">
            <span class="failed-row">第 {{ item.row_number }} 行：</span>
            <span v-for="err in item.errors" :key="err">{{ err }}</span>
          </div>
        </div>
      </div>

      <div class="step-actions">
        <van-button @click="restart">导入新文件</van-button>
        <van-button type="primary" @click="goToProducts">查看商品列表</van-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.import-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 16px;
  padding-bottom: 80px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
  color: #323233;
}
.steps-bar {
  margin-bottom: 20px;
  padding: 0;
}
.step-content {
  padding: 4px 0;
}

/* 操作指南 */
.guide-card {
  background: #f0f5ff;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 16px;
}
.guide-card h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #1a1a2e;
}
.guide-card ol {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: #555;
  line-height: 1.8;
}

/* 操作按钮行 */
.action-row {
  margin-bottom: 16px;
}

/* 上传区域 */
.upload-area {
  border: 2px dashed #dcdee0;
  border-radius: 8px;
  padding: 28px 16px;
  margin-bottom: 16px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s;
}
.upload-area:hover {
  border-color: #1989fa;
}
.upload-area.has-file {
  border-style: solid;
  border-color: #1989fa;
  padding: 12px 16px;
}
.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: #999;
  font-size: 14px;
}
.upload-hint {
  font-size: 12px;
  color: #bbb;
}
.upload-file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
.file-name {
  flex: 1;
  text-align: left;
  font-size: 14px;
  color: #323233;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.remove-btn {
  cursor: pointer;
}

/* 预览汇总 */
.preview-summary {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}
.summary-item {
  flex: 1;
  background: #f7f8fa;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}
.summary-item.valid {
  background: #e8f8ee;
}
.summary-item.invalid {
  background: #fff3eb;
}
.summary-num {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #323233;
}
.summary-item.valid .summary-num {
  color: #07c160;
}
.summary-item.invalid .summary-num {
  color: #ff976a;
}
.summary-label {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

/* 警告条 */
.warning-bar {
  background: #fff3eb;
  color: #ff976a;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 预览表格 */
.preview-table-wrap {
  overflow-x: auto;
  margin-bottom: 16px;
  border: 1px solid #ebedf0;
  border-radius: 8px;
}
.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 900px;
}
.preview-table th,
.preview-table td {
  padding: 8px 10px;
  text-align: left;
  border-bottom: 1px solid #ebedf0;
  white-space: nowrap;
}
.preview-table thead th {
  background: #f7f8fa;
  font-weight: 600;
  color: #646566;
  position: sticky;
  top: 0;
  z-index: 1;
}
.col-required {
  color: #ee0a24;
}
.col-num {
  width: 40px;
  text-align: center;
  color: #999;
  font-size: 12px;
}
.col-status {
  width: 72px;
}
.row-invalid {
  background: #fff8f7;
}
.row-invalid:hover {
  background: #ffede8;
}
.tag-ok {
  color: #07c160;
  font-size: 12px;
  font-weight: 500;
}
.tag-err {
  color: #ee0a24;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  position: relative;
}
.error-tip {
  display: none;
  position: absolute;
  top: 100%;
  right: 0;
  background: #fff;
  border: 1px solid #ebedf0;
  border-radius: 6px;
  padding: 8px 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 10;
  min-width: 200px;
  max-width: 320px;
  font-size: 12px;
  color: #ee0a24;
  line-height: 1.7;
  white-space: normal;
}
.tag-err:hover .error-tip {
  display: block;
}

/* 结果卡片 */
.result-card {
  background: #fff;
  border-radius: 12px;
  padding: 32px 24px;
  text-align: center;
  margin-bottom: 16px;
  border: 1px solid #ebedf0;
}
.result-card.all-success {
  border-color: #07c160;
}
.result-icon {
  margin-bottom: 12px;
}
.result-title {
  font-size: 18px;
  font-weight: 600;
  color: #323233;
  margin-bottom: 8px;
}
.result-stats {
  font-size: 14px;
  color: #666;
}
.stat-divider {
  margin: 0 8px;
  color: #dcdee0;
}
.stat-success {
  color: #07c160;
  font-weight: 500;
}
.stat-fail {
  color: #ee0a24;
  font-weight: 500;
}

/* 失败列表 */
.failed-list {
  margin-top: 16px;
  text-align: left;
  background: #fff8f7;
  border-radius: 8px;
  padding: 12px 16px;
}
.failed-list h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #ee0a24;
}
.failed-item {
  font-size: 13px;
  color: #555;
  line-height: 1.8;
}
.failed-row {
  font-weight: 500;
  color: #323233;
}

/* 底部操作 */
.step-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 8px;
}

/* PC 适配 */
@media (min-width: 1280px) {
  .import-page {
    padding: 24px 32px;
  }
  .preview-table th,
  .preview-table td {
    padding: 10px 14px;
  }
}
</style>
