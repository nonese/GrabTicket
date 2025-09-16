<template>
  <div class="container">
    <button v-if="token" class="logout-btn" @click="logout">退出登录</button>
    <button v-if="view === 'events'" class="orders-btn" @click="openOrders">我的抢票</button>
    <Login
      v-if="view === 'login'"
      @logged-in="onLoggedIn"
      @show-register="view = 'register'"
    />
    <Register
      v-else-if="view === 'register'"
      @registered="view = 'login'"
      @cancel="view = 'login'"
    />
    <div v-else-if="view === 'events'">
      <button v-if="isAdmin" class="admin-btn" @click="view = 'admin'">管理账户</button>
      <EventList @select-event="selectEvent" />
      <EventDetail v-if="currentEvent" :event="currentEvent" :key="currentEvent.id" />
    </div>
    <AdminUsers v-else-if="view === 'admin' && isAdmin" @close="view = 'events'" />
    <Modal v-if="showOrders" @close="showOrders = false">
      <h3>抢票记录</h3>
      <ul v-if="orders.length">
        <li v-for="o in orders" :key="o.id">
          {{ o.eventTitle }} - {{ o.ticketTypeLabel }} - {{ o.createdAtLabel }}
        </li>
      </ul>
      <p v-else-if="loadingOrders">加载中...</p>
      <p v-else>暂无抢票记录</p>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import Login from './components/Login.vue'
import Register from './components/Register.vue'
import EventList from './components/EventList.vue'
import EventDetail from './components/EventDetail.vue'
import AdminUsers from './components/AdminUsers.vue'
import Modal from './components/Modal.vue'

const token = ref(localStorage.getItem('token'))
const currentEvent = ref(null)
const username = ref(localStorage.getItem('username'))
const view = ref(token.value ? 'events' : 'login')
const isAdmin = computed(() => username.value === 'admin')
const showOrders = ref(false)
const orders = ref([])
const loadingOrders = ref(false)

function selectEvent(event) {
  currentEvent.value = event
}

function onLoggedIn(t) {
  token.value = t
  username.value = localStorage.getItem('username')
  view.value = 'events'
}

function logout() {
  token.value = null
  username.value = null
  currentEvent.value = null
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  view.value = 'login'
}

async function openOrders() {
  showOrders.value = true
  loadingOrders.value = true
  orders.value = []
  const tok = localStorage.getItem('token')
  try {
    const res = await axios.get('/orders/me', {
      headers: { Authorization: `Bearer ${tok}` }
    })
    orders.value = normalizeOrders(res.data)
  } catch (e) {
    orders.value = []
  } finally {
    loadingOrders.value = false
  }
}

function formatOrderDate(value) {
  if (!value && value !== 0) return '--'
  let date
  if (typeof value === 'number') {
    const ts = value < 1e12 ? value * 1000 : value
    date = new Date(ts)
  } else if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return '--'
    const isoLike = trimmed.replace(' ', 'T')
    const hasTimezone = /(Z|[+-]\d{2}:?\d{2})$/i.test(trimmed)
    const candidate = hasTimezone
      ? isoLike
      : `${isoLike}${isoLike.endsWith('Z') ? '' : 'Z'}`
    date = new Date(candidate)
    if (Number.isNaN(date.getTime())) {
      date = new Date(isoLike)
    }
    if (Number.isNaN(date.getTime())) {
      date = new Date(trimmed)
    }
  } else if (value instanceof Date) {
    date = value
  } else {
    return '--'
  }
  return Number.isNaN(date.getTime()) ? '--' : date.toLocaleString()
}

function normalizeOrders(list) {
  if (!Array.isArray(list)) {
    return []
  }
  return list
    .filter((item) => item && typeof item === 'object')
    .map((item) => {
      const order = { ...item }
      const createdAtSource =
        order.created_at ?? order.createdAt ?? order.created_at_value ?? order.createdat
      return {
        ...order,
        eventTitle: getOrderEventTitle(order),
        ticketTypeLabel: getOrderTicketTypeLabel(order),
        createdAtLabel: formatOrderDate(createdAtSource)
      }
    })
}

function getOrderEventTitle(order) {
  const event = order?.event
  if (event) {
    if (isNonEmptyString(event.title)) {
      return event.title.trim()
    }
    if (isNonEmptyString(event.name)) {
      return event.name.trim()
    }
  }
  const fallbackKeys = ['event_title', 'eventTitle', 'title']
  for (const key of fallbackKeys) {
    if (isNonEmptyString(order?.[key])) {
      return order[key].trim()
    }
  }
  return '未知活动'
}

function getOrderTicketTypeLabel(order) {
  const ticketType = order?.ticket_type
  if (ticketType) {
    if (isNonEmptyString(ticketType.seat_type)) {
      return ticketType.seat_type.trim()
    }
    if (isNonEmptyString(ticketType.name)) {
      return ticketType.name.trim()
    }
    if (isNonEmptyString(ticketType.label)) {
      return ticketType.label.trim()
    }
  }
  if (isNonEmptyString(order?.ticket_type)) {
    return order.ticket_type.trim()
  }
  const fallbackKeys = [
    'ticket_type_name',
    'ticketTypeName',
    'seat_type',
    'seatType',
    'ticketType',
    'ticket_name',
    'ticketName'
  ]
  for (const key of fallbackKeys) {
    if (isNonEmptyString(order?.[key])) {
      return order[key].trim()
    }
  }
  return '未知票档'
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0
}
</script>

<style>
.container {
  max-width: 750px;
  margin: 0 auto;
  padding: 1.5rem;
  text-align: center;
  position: relative;
}
.orders-btn {
  position: absolute;
  right: 1rem;
  top: 3.5rem;
  padding: 0.3rem 0.6rem;
  border: none;
  border-radius: 0.3rem;
  background: #10B981;
  color: #fff;
  cursor: pointer;
}
.admin-btn {
  position: absolute;
  right: 1rem;
  top: 1rem;
  padding: 0.3rem 0.6rem;
  border: none;
  border-radius: 0.3rem;
  background: #4F46E5;
  color: #fff;
  cursor: pointer;
}
.logout-btn {
  position: absolute;
  left: 1rem;
  top: 1rem;
  padding: 0.3rem 0.6rem;
  border: none;
  border-radius: 0.3rem;
  background: #DC2626;
  color: #fff;
  cursor: pointer;
}
</style>
