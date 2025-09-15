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
