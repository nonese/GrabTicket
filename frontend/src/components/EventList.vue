<template>
  <div class="events">
    <h2>活动列表</h2>
    <form class="create-form" @submit.prevent="createEvent">
      <input v-model="form.title" placeholder="活动名称" required />
      <input v-model="form.organizer" placeholder="主办方" required />
      <input v-model="form.location" placeholder="地点" required />
      <input type="datetime-local" v-model="form.start_time" required />
      <input type="datetime-local" v-model="form.end_time" required />
      <input type="file" @change="onFileChange" />
      <button type="submit">添加活动</button>
    </form>
    <div class="cards">
      <div class="card" v-for="event in events" :key="event.id" @click="select(event)">
        <img v-if="event.cover_image" :src="event.cover_image" class="card-img" />
        <div class="card-body">
          <h3>{{ event.title }}</h3>
          <p>{{ formatDate(event.start_time) }}</p>
          <p>{{ event.location }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const emit = defineEmits(['select-event'])
const events = ref([])
const form = ref({
  title: '',
  organizer: '',
  location: '',
  start_time: '',
  end_time: ''
})
const imageFile = ref(null)

onMounted(loadEvents)

async function loadEvents() {
  const token = localStorage.getItem('token')
  const res = await axios.get('/events', {
    headers: { Authorization: `Bearer ${token}` }
  })
  events.value = res.data
}

function select(event) {
  emit('select-event', event)
}

function onFileChange(e) {
  imageFile.value = e.target.files[0]
}

function formatDate(str) {
  return new Date(str).toLocaleString()
}

async function createEvent() {
  const token = localStorage.getItem('token')
  const fd = new FormData()
  fd.append('title', form.value.title)
  fd.append('organizer', form.value.organizer)
  fd.append('location', form.value.location)
  fd.append('start_time', form.value.start_time)
  fd.append('end_time', form.value.end_time)
  if (imageFile.value) {
    fd.append('image', imageFile.value)
  }
  const res = await axios.post('/events', fd, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    }
  })
  events.value.push(res.data)
  form.value = { title: '', organizer: '', location: '', start_time: '', end_time: '' }
  imageFile.value = null
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
.create-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.create-form input {
  padding: 0.3rem;
  border: 1px solid #ccc;
  border-radius: 0.3rem;
}
.create-form button {
  background: #5A9AFF;
  color: #fff;
  border: none;
  border-radius: 0.5rem;
  padding: 0.4rem 0.8rem;
  cursor: pointer;
}
.cards {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}
.card {
  width: 200px;
  border: 1px solid #eee;
  border-radius: 0.5rem;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.card-img {
  width: 100%;
  height: 120px;
  object-fit: cover;
}
.card-body {
  padding: 0.5rem;
}
.card-body h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
  color: #ff5f00;
}
.card-body p {
  margin: 0;
  font-size: 0.9rem;
}
</style>

