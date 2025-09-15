<template>
  <div class="event-detail">
    <h3>{{ event.title }}</h3>
    <div class="seat-map" v-if="event.seat_map_url">
      <img :src="event.seat_map_url" class="seat-image" />
    </div>
    <div class="ticket-options">
      <button
        v-for="t in tickets"
        :key="t.id"
        class="ticket-btn"
        :class="{ active: selected && selected.id === t.id, disabled: !started }"
        @click="started && (selected = t)"
      >
        {{ t.seat_type }} ¥{{ t.price }} (剩余{{ t.available_qty }})
      </button>
    </div>
    <button class="confirm-btn" :disabled="!started || !selected" @click="confirm">
      确定
    </button>
    <p v-if="!started">距离开抢还有：{{ formatTime(timeLeft) }}</p>
    <p v-if="message">{{ message }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const props = defineProps({
  event: Object
})

const message = ref('')
const tickets = ref([])
const timeLeft = ref(0)
const started = computed(() => timeLeft.value <= 0)
const selected = ref(null)
let ws
let timer

onMounted(() => {
  tickets.value = props.event.ticket_types || []
  const saleStart = new Date(props.event.sale_start_time).getTime()
  const updateCountdown = () => {
    const diff = saleStart - Date.now()
    timeLeft.value = diff > 0 ? diff : 0
  }
  updateCountdown()
  timer = setInterval(updateCountdown, 1000)
  const token = localStorage.getItem('token')
  const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/events/${props.event.id}?token=${token}`
  ws = new WebSocket(wsUrl)
  ws.onmessage = (evt) => {
    const data = JSON.parse(evt.data)
    if (data.type === 'seat_counts') {
      tickets.value = tickets.value.map(t => {
        const match = data.tickets.find(dt => dt.ticket_type_id === t.id)
        return match ? { ...t, available_qty: match.available_qty } : t
      })
      if (selected.value) {
        const matchSel = tickets.value.find(tt => tt.id === selected.value.id)
        if (matchSel) selected.value = matchSel
      }
    } else if (data.type === 'grab_result') {
      if (data.status === 'success') {
        message.value = '抢票成功！订单号: ' + data.order_id
      } else {
        const alts = (data.alternatives || []).map(a => `${a.seat_type}(${a.available_qty})`).join(', ')
        message.value = '抢票失败，座位已满' + (alts ? '，可选：' + alts : '')
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
  const t = selected.value
  if (window.confirm(`需要支付${t.price}水晶能量币，是否继续？`)) {
    grab(t.id)
  }
}

function formatTime(ms) {
  const total = Math.floor(ms / 1000)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
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
</style>
