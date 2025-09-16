<template>
  <div class="admin-orders">
    <h2>抢票记录</h2>
    <div class="actions">
      <button @click="loadOrders" :disabled="loading">
        {{ loading ? '加载中...' : '刷新' }}
      </button>
      <button
        @click="exportExcel"
        :disabled="exporting || !orders.length"
      >
        {{ exporting ? '导出中...' : '导出Excel' }}
      </button>
      <button class="secondary" @click="$emit('close')">返回</button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <table v-if="!loading && paginatedOrders.length">
      <thead>
        <tr>
          <th>订单ID</th>
          <th>用户名</th>
          <th>活动名称</th>
          <th>票档</th>
          <th>票价</th>
          <th>抢票时间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="order in paginatedOrders" :key="order.id">
          <td>{{ order.id }}</td>
          <td>{{ order.user?.username || '未知用户' }}</td>
          <td>{{ order.event?.title || '未知活动' }}</td>
          <td>{{ order.ticket_type?.seat_type || '--' }}</td>
          <td>{{ formatPrice(order.ticket_type?.price) }}</td>
          <td>{{ formatDate(order.created_at) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="loading" class="status">加载中...</p>
    <p v-else class="status">暂无抢票记录</p>
    <div class="pagination" v-if="!loading && totalPages > 1">
      <button @click="prevPage" :disabled="currentPage === 1">上一页</button>
      <span>{{ currentPage }} / {{ totalPages }}</span>
      <button @click="nextPage" :disabled="currentPage === totalPages">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const orders = ref([])
const loading = ref(false)
const exporting = ref(false)
const error = ref('')
const currentPage = ref(1)
const pageSize = 10

const totalPages = computed(() => Math.ceil(orders.value.length / pageSize) || 1)
const paginatedOrders = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return orders.value.slice(start, start + pageSize)
})

onMounted(loadOrders)

async function loadOrders() {
  loading.value = true
  error.value = ''
  const token = localStorage.getItem('token')
  try {
    const res = await axios.get('/admin/orders', {
      headers: { Authorization: `Bearer ${token}` }
    })
    let raw = res.data
    if (typeof raw === 'string') {
      try {
        raw = JSON.parse(raw)
      } catch (e) {
        raw = []
      }
    }
    const list = Array.isArray(raw)
      ? raw
      : Array.isArray(raw?.orders)
        ? raw.orders
        : []
    orders.value = list.filter((item) => item && typeof item.id === 'number')
    currentPage.value = 1
  } catch (e) {
    orders.value = []
    currentPage.value = 1
    error.value = e.response?.data?.detail || '加载抢票记录失败'
  } finally {
    loading.value = false
  }
}

function formatDate(value) {
  if (!value) return '--'
  let date
  if (typeof value === 'number') {
    const ts = value < 1e12 ? value * 1000 : value
    date = new Date(ts)
  } else if (typeof value === 'string') {
    const hasTimezone = /(Z|[+-]\d{2}:\d{2})$/i.test(value)
    const normalized = hasTimezone ? value : `${value}Z`
    date = new Date(normalized)
    if (Number.isNaN(date.getTime())) {
      date = new Date(value)
    }
  } else if (value instanceof Date) {
    date = value
  } else {
    return '--'
  }
  return Number.isNaN(date.getTime()) ? '--' : date.toLocaleString()
}

function formatPrice(value) {
  if (value === null || value === undefined || value === '') return '--'
  const num = Number(value)
  if (Number.isNaN(num)) return String(value)
  return num.toFixed(2)
}

function nextPage() {
  if (currentPage.value < totalPages.value) currentPage.value += 1
}

function prevPage() {
  if (currentPage.value > 1) currentPage.value -= 1
}

async function exportExcel() {
  if (!orders.value.length) return
  const token = localStorage.getItem('token')
  exporting.value = true
  error.value = ''
  try {
    const res = await axios.get('/admin/orders/export', {
      headers: { Authorization: `Bearer ${token}` },
      responseType: 'blob'
    })
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const stamp = new Date().toISOString().replace(/[-:]/g, '').split('.')[0]
    link.href = url
    link.download = `orders_${stamp}.xlsx`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    error.value = e.response?.data?.detail || '导出失败，请稍后重试'
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped>
.admin-orders {
  background: #fff;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-top: 1rem;
  text-align: left;
}

.actions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

button {
  padding: 0.4rem 0.8rem;
  border: none;
  border-radius: 0.4rem;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

button.secondary {
  background: #6b7280;
}

.error {
  color: #dc2626;
  margin-bottom: 0.5rem;
}

.status {
  margin: 1rem 0;
  color: #6b7280;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
}

th, td {
  border: 1px solid #ddd;
  padding: 0.5rem;
  text-align: center;
  font-size: 0.9rem;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.pagination button {
  background: #4f46e5;
  padding: 0.3rem 0.6rem;
}

.pagination span {
  color: #374151;
}
</style>
