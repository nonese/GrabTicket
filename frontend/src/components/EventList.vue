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
