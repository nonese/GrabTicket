<template>
  <div class="event-detail">
    <h3>{{ event.title }}</h3>
    <div class="coin-info">
      <span>当前能量币：{{ coins }}</span>
      <button class="edit-coins-btn" @click="openEditCoins">修改能量币</button>
    </div>
    <div class="seat-map" v-if="event.seat_map_url">
      <img :src="event.seat_map_url" class="seat-image" />
    </div>
    <div class="ticket-options">
      <button
        v-for="t in tickets"
        :key="t.id"
        class="ticket-btn"
        :class="{ active: selected && selected.id === t.id, disabled: !started || t.available_qty === 0 }"
        @click="started && t.available_qty > 0 && (selected = t)"
      >
        {{ t.seat_type }} ¥{{ t.price }} (剩余{{ t.available_qty }})
      </button>
    </div>
    <button class="confirm-btn" :disabled="!started || !selected || selected.available_qty === 0" @click="confirm">
      确定
    </button>
    <p v-if="!started">距离开抢还有：{{ formatTime(timeLeft) }}</p>
    <p v-if="message">{{ message }}</p>

    <Modal v-if="showConfirm" @close="showConfirm = false">
      <p>需要支付{{ selected.price }}水晶能量币，是否继续？</p>
      <div class="modal-actions">
        <button @click="doGrab">确认</button>
        <button class="secondary" @click="showConfirm = false">取消</button>
      </div>
    </Modal>
    <Modal v-if="showEditCoins" @close="closeEditCoins">
      <h4>修改能量币</h4>
      <div class="edit-coins-form">
        <label for="coin-input">新的能量币数量</label>
        <input
          id="coin-input"
          type="number"
          min="0"
          v-model="editCoinsValue"
          :disabled="updatingCoins"
        />
        <p v-if="editCoinsError" class="edit-coins-error">{{ editCoinsError }}</p>
        <div class="modal-actions">
          <button @click="submitEditCoins" :disabled="updatingCoins">保存</button>
          <button class="secondary" @click="closeEditCoins" :disabled="updatingCoins">取消</button>
        </div>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import axios from 'axios'
import Modal from './Modal.vue'

const props = defineProps({
  event: Object
})

const message = ref('')
const tickets = ref([])
const timeLeft = ref(0)
const started = computed(() => timeLeft.value <= 0)
const selected = ref(null)
const showConfirm = ref(false)
const coins = ref(0)
const showEditCoins = ref(false)
const editCoinsValue = ref('')
const editCoinsError = ref('')
const updatingCoins = ref(false)
let ws
let timer

onMounted(() => {
  tickets.value = props.event.ticket_types || []
  const saleStart = Date.parse(props.event.sale_start_time + 'Z')
  const updateCountdown = () => {
    timeLeft.value = Math.max(0, saleStart - Date.now())
  }
  updateCountdown()
  timer = setInterval(updateCountdown, 1000)
  const token = localStorage.getItem('token')
  if (!token) {
    message.value = '请先登录'
    return
  }
  axios.get('/users/me', {
    headers: { Authorization: `Bearer ${token}` }
  }).then(res => {
    coins.value = res.data.energy_coins
  })
  // Allow the websocket host to be configured via VITE_WS_HOST so the
  // connection works when the frontend and backend run on different hosts or
  // ports. If the variable is not set we fall back to the current location.
  const wsProtocol = location.protocol === 'https:' ? 'wss' : 'ws'
  const wsHost = import.meta.env.VITE_WS_HOST || location.host
  const wsUrl = `${wsProtocol}://${wsHost}/ws/events/${props.event.id}?token=${token}`
  ws = new WebSocket(wsUrl)
  ws.onerror = () => {
    message.value = '连接服务器失败'
  }
  ws.onclose = (evt) => {
    if (!evt.wasClean) {
      message.value = '连接已断开'
    }
  }
  ws.onmessage = (evt) => {
    const data = JSON.parse(evt.data)
    if (data.type === 'seat_counts') {
      tickets.value = tickets.value.map(t => {
        const match = data.tickets.find(dt => dt.ticket_type_id === t.id)
        return match ? { ...t, available_qty: match.available_qty } : t
      })
      if (selected.value) {
        const matchSel = tickets.value.find(tt => tt.id === selected.value.id)
        if (matchSel && matchSel.available_qty > 0) {
          selected.value = matchSel
        } else if (matchSel) {
          selected.value = null
        }
      }
    } else if (data.type === 'grab_result') {
      if (data.status === 'success') {
        message.value = '抢票成功！订单号: ' + data.order_id
        coins.value -= selected.value.price
      } else {
        const alts = (data.alternatives || []).map(a => `${a.seat_type}(${a.available_qty})`).join(', ')
        if (data.reason === '座位已满') {
          message.value = '抢票失败，座位已满' + (alts ? '，可选：' + alts : '')
        } else {
          message.value = '抢票失败：' + data.reason
        }
      }
    }
  }
})

onUnmounted(() => {
  if (ws) ws.close()
  if (timer) clearInterval(timer)
})

function grab(ticketTypeId) {
  ws?.send(JSON.stringify({ action: 'grab', ticket_type_id: ticketTypeId }))
}

function confirm() {
  if (!selected.value) return
  if (!started.value) {
    message.value = '未到开抢时间'
    return
  }
  showConfirm.value = true
}

function doGrab() {
  const t = selected.value
  showConfirm.value = false
  grab(t.id)
}

function formatTime(ms) {
  const total = Math.floor(ms / 1000)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function openEditCoins() {
  editCoinsValue.value = coins.value != null ? String(coins.value) : '0'
  editCoinsError.value = ''
  showEditCoins.value = true
}

function closeEditCoins() {
  if (updatingCoins.value) return
  showEditCoins.value = false
  editCoinsError.value = ''
}

async function submitEditCoins() {
  const token = localStorage.getItem('token')
  if (!token) {
    editCoinsError.value = '请先登录后再修改能量币'
    return
  }
  const trimmed = (editCoinsValue.value ?? '').toString().trim()
  if (!trimmed) {
    editCoinsError.value = '请输入能量币数量'
    return
  }
  if (!/^\d+$/.test(trimmed)) {
    editCoinsError.value = '请输入不小于0的整数'
    return
  }
  const parsed = Number.parseInt(trimmed, 10)
  updatingCoins.value = true
  editCoinsError.value = ''
  try {
    const res = await axios.put(
      '/users/me/coins',
      { energy_coins: parsed },
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    )
    coins.value = res.data.energy_coins
    message.value = '能量币已更新'
    showEditCoins.value = false
  } catch (err) {
    const detail = err?.response?.data?.detail
    editCoinsError.value = detail || '更新失败，请稍后再试'
  } finally {
    updatingCoins.value = false
  }
}
</script>

<style scoped>
.event-detail {
  background: #fff;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-top: 1rem;
  text-align: left;
}
.event-detail h3 {
  margin-top: 0;
  color: #ff5f00;
}
.seat-map {
  position: relative;
  margin-top: 1rem;
  border: 1px solid #ddd;
  display: inline-block;
}
.seat-image {
  display: block;
  max-width: 100%;
}
.ticket-options {
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.ticket-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  background: #f5f5f5;
  cursor: pointer;
}
.ticket-btn.active {
  border-color: #ff5f00;
  background: #ffe8d9;
}
.ticket-btn.disabled {
  pointer-events: none;
  opacity: 0.6;
}
.confirm-btn {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #ff5f00;
  color: #fff;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
}
.confirm-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}
.modal-actions {
  margin-top: 1rem;
  text-align: center;
}
.modal-actions button {
  margin: 0 0.3rem;
  padding: 0.3rem 0.6rem;
  border: none;
  border-radius: 0.3rem;
  background: #4F46E5;
  color: #fff;
  cursor: pointer;
}
.coin-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0.5rem 0 0;
}
.edit-coins-btn {
  padding: 0.3rem 0.6rem;
  border: none;
  border-radius: 0.3rem;
  background: #2563EB;
  color: #fff;
  cursor: pointer;
  font-size: 0.85rem;
}
.edit-coins-btn:hover {
  background: #1D4ED8;
}
.edit-coins-btn:focus {
  outline: none;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.3);
}
.edit-coins-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 240px;
}
.edit-coins-form input {
  padding: 0.4rem 0.5rem;
  border: 1px solid #D1D5DB;
  border-radius: 0.3rem;
}
.edit-coins-form input:disabled {
  background: #F3F4F6;
}
.edit-coins-error {
  color: #DC2626;
  margin: 0;
  font-size: 0.85rem;
}
.modal-actions button.secondary {
  background: #6B7280;
}
.modal-actions button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.modal-actions button.secondary:disabled {
  background: #9CA3AF;
}
</style>
