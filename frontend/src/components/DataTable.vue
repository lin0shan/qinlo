<script setup lang="ts" generic="T extends Record<string, unknown>">
/**
 * DataTable 自建表格组件
 * CSS Grid 实现，零依赖。满足 5000 SKU 级别数据量。
 *
 * Props:
 *   columns  - 列定义 [{key, title, width?, sortable?, align?}]
 *   data     - 数据数组
 *   loading  - 加载状态
 *   emptyText - 空数据提示
 *
 * Events:
 *   @row-click(row, index)  - 行点击
 *   @sort(key, direction)   - 排序变更
 */
import { ref, computed } from 'vue'

export interface ColumnDef {
  key: string
  title: string
  width?: string
  sortable?: boolean
  align?: 'left' | 'center' | 'right'
}

const props = withDefaults(
  defineProps<{
    columns: ColumnDef[]
    data: T[]
    loading?: boolean
    emptyText?: string
  }>(),
  {
    loading: false,
    emptyText: '暂无数据',
  }
)

const emit = defineEmits<{
  (e: 'row-click', row: T, index: number): void
  (e: 'sort', key: string, direction: 'asc' | 'desc'): void
}>()

const sortKey = ref('')
const sortDir = ref<'asc' | 'desc'>('asc')

function handleSort(col: ColumnDef) {
  if (!col.sortable) return
  if (sortKey.value === col.key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = col.key
    sortDir.value = 'asc'
  }
  emit('sort', sortKey.value, sortDir.value)
}

function handleRowClick(row: T, index: number) {
  emit('row-click', row, index)
}

const gridColumns = computed(() =>
  props.columns
    .map((c) => c.width || '1fr')
    .join(' ')
)
</script>

<template>
  <div class="dt-wrapper">
    <!-- 加载态 -->
    <van-loading v-if="loading" class="dt-loading" size="24px" text-color="#999">
      加载中...
    </van-loading>

    <!-- 空状态 -->
    <van-empty v-else-if="data.length === 0" :description="emptyText" />

    <!-- 表格 -->
    <div v-else class="dt-table">
      <!-- Header -->
      <div class="dt-header" :style="{ gridTemplateColumns: gridColumns }">
        <div
          v-for="col in columns"
          :key="col.key"
          class="dt-th"
          :class="{ sortable: col.sortable, active: sortKey === col.key }"
          :style="{ textAlign: col.align || 'left' }"
          @click="handleSort(col)"
        >
          {{ col.title }}
          <span v-if="col.sortable && sortKey === col.key" class="dt-sort-icon">
            {{ sortDir === 'asc' ? '▲' : '▼' }}
          </span>
        </div>
      </div>

      <!-- 表体 -->
      <div class="dt-body">
        <div
          v-for="(row, idx) in data"
          :key="idx"
          class="dt-row"
          :style="{ gridTemplateColumns: gridColumns }"
          @click="handleRowClick(row, idx)"
        >
          <div
            v-for="col in columns"
            :key="col.key"
            class="dt-td"
            :style="{ textAlign: col.align || 'left' }"
          >
            <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">
              {{ row[col.key] }}
            </slot>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dt-wrapper {
  width: 100%;
  background: #fff;
  border-radius: 4px;
  overflow: hidden;
}
.dt-loading {
  padding: 40px 0;
  text-align: center;
}
.dt-table {
  width: 100%;
}
.dt-header,
.dt-row {
  display: grid;
  align-items: center;
}
.dt-header {
  background: #f7f8fa;
  border-bottom: 1px solid #ebedf0;
  font-weight: 600;
  font-size: 13px;
  color: #646566;
}
.dt-th {
  padding: 10px 12px;
  user-select: none;
}
.dt-th.sortable {
  cursor: pointer;
}
.dt-th.sortable:hover,
.dt-th.active {
  color: #ff6b81;
}
.dt-sort-icon {
  font-size: 10px;
  margin-left: 4px;
}
.dt-body {
  max-height: calc(100vh - 180px);
  overflow-y: auto;
}
.dt-row {
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.15s;
}
.dt-row:hover {
  background: #f7f8fa;
}
.dt-row:last-child {
  border-bottom: none;
}
.dt-td {
  padding: 10px 12px;
  font-size: 13px;
  color: #323233;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
