<template>
  <div class="event-detail">
    <h3>{{ event.title }}</h3>
    <div class="seat-map" v-if="event.seat_map_url">
      <img :src="event.seat_map_url" class="seat-image" />
      <div
        v-for="t in tickets"
        :key="t.id"
        class="seat-block"
        :style="{left: t.pos_x + 'px', top: t.pos_y + 'px'}"
        @click="tryGrab(t)"
      >
        {{ t.seat_type }}({{ t.available_qty }})
      </div>
    </div>
    <p v-if="message">{{ message }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  event: Object
})

const message = ref('')
const tickets = ref([])
let ws

onMounted(() => {
  tickets.value = props.event.ticket_types || []
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
})

function grab(ticketTypeId) {
  ws?.send(JSON.stringify({ action: 'grab', ticket_type_id: ticketTypeId }))
}

function tryGrab(t) {
  if (window.confirm(`需要支付${t.price}水晶能量币，是否继续？`)) {
    grab(t.id)
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
.seat-block {
  position: absolute;
  width: 50px;
  height: 50px;
  background: rgba(90,154,255,0.8);
  color: #fff;
  text-align: center;
  line-height: 50px;
  cursor: pointer;
  border-radius: 4px;
  user-select: none;
}
</style>
