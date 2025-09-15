<template>
  <div class="event-detail">
    <h3>{{ event.title }}</h3>
    <img :src="event.seat_map_url" alt="seat map" v-if="event.seat_map_url" />
    <div class="tickets">
      <div v-for="t in event.ticket_types" :key="t.id" class="ticket">
        <span>{{ t.seat_type }} - ￥{{ t.price }}</span>
        <button @click="buy(t.id)" :disabled="t.available_qty === 0">抢票</button>
        <span v-if="t.available_qty === 0">售罄</span>
      </div>
    </div>
    <p v-if="message">{{ message }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const props = defineProps({
  event: Object
})

const message = ref('')

async function buy(ticketTypeId) {
  const token = localStorage.getItem('token')
  try {
    const res = await axios.post(`/events/${props.event.id}/tickets`, null, {
      params: { ticket_type_id: ticketTypeId },
      headers: { Authorization: `Bearer ${token}` }
    })
    message.value = '抢票成功！订单号: ' + res.data.id
  } catch (e) {
    message.value = '抢票失败'
  }
}
</script>

<style scoped>
.event-detail {
  border: 1px solid #ddd;
  padding: 1rem;
  margin-top: 1rem;
}
.tickets {
  margin-top: 1rem;
}
.ticket {
  margin-bottom: 0.5rem;
}
.ticket button {
  margin-left: 1rem;
}
</style>
