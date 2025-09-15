<template>
  <div class="event-detail">
    <h3>{{ event.title }}</h3>
    <img :src="event.seat_map_url" alt="seat map" v-if="event.seat_map_url" />
    <div class="tickets">
      <div v-for="t in tickets" :key="t.id" class="ticket">
        <span>{{ t.seat_type }} - ￥{{ t.price }}</span>
        <button @click="grab(t.id)" :disabled="t.available_qty === 0">抢票</button>
        <span v-if="t.available_qty === 0">售罄</span>
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
.tickets {
  margin-top: 1rem;
}
.ticket {
  margin-bottom: 0.5rem;
}
.ticket button {
  margin-left: 1rem;
  background: #5A9AFF;
  color: #fff;
  border: none;
  border-radius: 0.5rem;
  padding: 0.3rem 0.6rem;
  cursor: pointer;
}
</style>
