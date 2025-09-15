<template>
  <div class="events">
    <h2>活动列表</h2>
    <ul>
      <li v-for="event in events" :key="event.id" @click="select(event)">
        {{ event.title }}
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const emit = defineEmits(['select-event'])
const events = ref([])

onMounted(async () => {
  const token = localStorage.getItem('token')
  const res = await axios.get('/events', {
    headers: { Authorization: `Bearer ${token}` }
  })
  events.value = res.data
})

function select(event) {
  emit('select-event', event)
}
</script>

<style scoped>
.events {
  background: #fff;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-top: 1rem;
  text-align: left;
}
.events h2 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.3rem;
  color: #ff5f00;
}
.events ul {
  list-style: none;
  padding: 0;
}
.events li {
  padding: 0.5rem;
  border-bottom: 1px solid #eee;
  cursor: pointer;
}
.events li:hover {
  background: #f0f0f0;
}
</style>
