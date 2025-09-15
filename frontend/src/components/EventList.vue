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
      <input type="file" @change="onSeatMapChange" />
      <div class="block-form">
        <input v-model="newBlock.seat_type" placeholder="座位类型" />
        <input type="number" v-model.number="newBlock.price" placeholder="价格" />
        <input type="number" v-model.number="newBlock.available_qty" placeholder="数量" />
        <button type="button" @click="addBlock">添加座位方块</button>
      </div>
      <div class="seat-map" v-if="seatMapPreview" ref="seatMapRef" @mousemove="onMove" @mouseup="stopDrag">
        <img :src="seatMapPreview" class="seat-image" />
        <div
          v-for="(b, idx) in seatBlocks"
          :key="idx"
          class="seat-block"
          :style="{left: b.pos_x + 'px', top: b.pos_y + 'px'}"
          @mousedown.prevent="startDrag(idx, $event)"
        >
          {{ b.seat_type }}({{ b.available_qty }})
        </div>
      </div>
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
const seatMapFile = ref(null)
const seatMapPreview = ref(null)
const seatBlocks = ref([])
const newBlock = ref({ seat_type: '', price: 0, available_qty: 0 })
const dragging = ref({ index: null, offsetX: 0, offsetY: 0 })
const seatMapRef = ref(null)

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

function onSeatMapChange(e) {
  seatMapFile.value = e.target.files[0]
  if (seatMapFile.value) {
    seatMapPreview.value = URL.createObjectURL(seatMapFile.value)
  }
}

function addBlock() {
  if (!newBlock.value.seat_type) return
  seatBlocks.value.push({ ...newBlock.value, pos_x: 0, pos_y: 0 })
  newBlock.value = { seat_type: '', price: 0, available_qty: 0 }
}

function startDrag(idx, e) {
  dragging.value = { index: idx, offsetX: e.offsetX, offsetY: e.offsetY }
}

function onMove(e) {
  if (dragging.value.index === null) return
  const rect = seatMapRef.value.getBoundingClientRect()
  const b = seatBlocks.value[dragging.value.index]
  b.pos_x = e.clientX - rect.left - dragging.value.offsetX
  b.pos_y = e.clientY - rect.top - dragging.value.offsetY
}

function stopDrag() {
  dragging.value.index = null
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
  if (seatMapFile.value) {
    fd.append('seat_map', seatMapFile.value)
  }
  fd.append('ticket_types', JSON.stringify(seatBlocks.value))
  const res = await axios.post('/events', fd, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    }
  })
  events.value.push(res.data)
  form.value = { title: '', organizer: '', location: '', start_time: '', end_time: '' }
  imageFile.value = null
  seatMapFile.value = null
  seatMapPreview.value = null
  seatBlocks.value = []
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
.block-form {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
  align-items: center;
}
.seat-map {
  position: relative;
  margin-top: 0.5rem;
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
  cursor: move;
  border-radius: 4px;
  user-select: none;
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

