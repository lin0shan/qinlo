<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { showToast, showDialog } from 'vant'

const API = '/api/v1'

/**
 * 将后端返回的 UTC ISO 字符串转换为北京时间显示格式
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

const settings = ref({
  shop_name: '个人商业助手',
  low_stock_threshold: 10,
  backup_auto_enabled: false,
  backup_interval_hours: 24,
  barcode_prefix: 'BH',
})

const backupList = ref<any[]>([])
const saving = ref(false)

async function loadSettings() {
  try {
    const res = await fetch(`${API}/settings`)
    settings.value = await res.json()
  } catch { /* offline */ }
}

async function saveSettings() {
  saving.value = true
  try {
    const res = await fetch(`${API}/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings.value),
    })
    if (res.ok) showToast('设置已保存')
  } finally {
    saving.value = false
  }
}

async function createBackup() {
  try {
    const res = await fetch(`${API}/backup`, { method: 'POST' })
    const data = await res.json()
    showToast(`备份完成: ${data.file_name}`)
    loadBackups()
  } catch {
    showToast('备份失败')
  }
}

async function downloadBackup() {
  const a = document.createElement('a')
  a.href = `${API}/backup/download`
  a.download = 'backup.db'
  a.click()
}

async function loadBackups() {
  try {
    const res = await fetch(`${API}/backup/list`)
    backupList.value = await res.json()
  } catch { /* offline */ }
}

async function restoreBackup() {
  showDialog({
    title: '数据恢复',
    message: '恢复将覆盖当前数据，建议先备份。确定继续？',
    showCancelButton: true,
  }).then(async () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.db'
    input.onchange = async () => {
      const file = input.files?.[0]
      if (!file) return
      const form = new FormData()
      form.append('file', file)
      try {
        const res = await fetch(`${API}/restore`, { method: 'POST', body: form })
        if (res.ok) showToast('数据恢复成功，请刷新页面')
        else showToast('恢复失败')
      } catch {
        showToast('恢复失败')
      }
    }
    input.click()
  }).catch(() => {})
}

onMounted(() => {
  loadSettings()
  loadBackups()
})
</script>

<template>
  <div class="page">
    <van-nav-bar title="系统设置" fixed placeholder />

    <!-- 店铺设置 -->
    <van-cell-group title="店铺设置">
      <van-field v-model="settings.shop_name" label="店铺名称" />
      <van-field v-model="settings.low_stock_threshold" label="低库存阈值" type="digit" />
      <van-field v-model="settings.barcode_prefix" label="店内条码前缀" maxlength="4" />
    </van-cell-group>

    <!-- 自动备份 -->
    <van-cell-group title="自动备份" style="margin-top:8px">
      <van-cell title="启用定时备份">
        <template #right-icon>
          <van-switch v-model="settings.backup_auto_enabled" size="20" />
        </template>
      </van-cell>
      <van-field v-if="settings.backup_auto_enabled" v-model="settings.backup_interval_hours"
        label="备份间隔(小时)" type="digit" />
    </van-cell-group>

    <van-button type="primary" block @click="saveSettings" :loading="saving"
      style="margin:16px">保存设置</van-button>

    <!-- 备份恢复 -->
    <van-cell-group title="数据备份与恢复" style="margin-top:8px">
      <van-cell title="手动备份" label="创建当前数据库的快照" is-link @click="createBackup">
        <template #icon><van-icon name="down" style="margin-right:8px;color:#1989fa" /></template>
      </van-cell>
      <van-cell title="下载最新备份" label="下载 .db 文件到本地" is-link @click="downloadBackup">
        <template #icon><van-icon name="down" style="margin-right:8px;color:#07c160" /></template>
      </van-cell>
      <van-cell title="恢复数据" label="上传备份文件恢复" is-link @click="restoreBackup">
        <template #icon><van-icon name="upgrade" style="margin-right:8px;color:#ee0a24" /></template>
      </van-cell>
    </van-cell-group>

    <!-- 备份历史 -->
    <van-cell-group v-if="backupList.length > 0" title="备份历史" style="margin-top:8px">
      <van-cell v-for="b in backupList" :key="b.id"
        :title="b.file_name"
        :label="formatBeijingTime(b.created_at)"
        :value="(b.file_size / 1024).toFixed(0) + ' KB'" />
    </van-cell-group>
  </div>
</template>
