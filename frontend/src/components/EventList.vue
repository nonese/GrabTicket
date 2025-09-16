<template>
  <div class="events">
    <h2>活动列表</h2>
    <form
      v-if="isAdmin"
      class="create-form"
      @submit.prevent="editingId ? updateEvent() : createEvent()"
    >
      <div class="field">
        <label>活动名称
          <input v-model="form.title" required />
        </label>
      </div>
      <div class="field">
        <label>主办方
          <input v-model="form.organizer" required />
        </label>
      </div>
      <div class="field">
        <label>地点
          <input v-model="form.location" required />
        </label>
      </div>
      <div class="field">
        <label>开售时间
          <input type="datetime-local" v-model="form.sale_start_time" required />
        </label>
      </div>
      <div class="field">
        <label>开始时间
          <input type="datetime-local" v-model="form.start_time" required />
        </label>
      </div>
      <div class="field">
        <label>封面图片
          <input type="file" @change="onFileChange" />
        </label>
      </div>
      <div class="field">
        <label>座位图
          <input type="file" @change="onSeatMapChange" />
        </label>
      </div>
      <div class="field field-checkbox">
        <label class="checkbox-label">
          <input type="checkbox" v-model="form.limit_one_ticket_per_user" />
          每个账户限购一张
        </label>
        <span class="checkbox-hint">开启后，同一账户只能抢购一张门票</span>
      </div>
      <div class="block-form">
        <label>票档名称
          <input v-model="newTicket.seat_type" />
        </label>
        <label>价格
          <input type="number" min="0" step="0.01" v-model.number="newTicket.price" />
        </label>
        <label>数量
          <input type="number" min="0" v-model.number="newTicket.available_qty" />
        </label>
        <button type="button" @click="addTicket">添加票档</button>
      </div>
      <div class="ticket-editor" v-if="ticketTypes.length">
        <div class="ticket-editor-row ticket-editor-header">
          <span>票档名称</span>
          <span>价格</span>
          <span>数量</span>
          <span class="ticket-editor-actions">操作</span>
        </div>
        <div class="ticket-editor-row" v-for="(t, idx) in ticketTypes" :key="idx">
          <input v-model="t.seat_type" placeholder="票档名称" />
          <input type="number" min="0" step="0.01" v-model.number="t.price" />
          <input type="number" min="0" v-model.number="t.available_qty" />
          <button type="button" class="remove-ticket-btn" @click="removeTicket(idx)">删除</button>
        </div>
      </div>
      <div class="seat-map" v-if="seatMapPreview">
        <img :src="seatMapPreview" class="seat-image" />
      </div>
      <button type="submit">{{ editingId ? '更新活动' : '添加活动' }}</button>
      <button v-if="editingId" type="button" @click="cancelEdit">取消</button>
    </form>
    <div class="cards">
      <div
        class="card"
        v-for="event in events"
        :key="event.id"
        @click="select(event)"
      >
        <img v-if="event.cover_image" :src="event.cover_image" class="card-img" />
        <div class="card-body">
          <h3>{{ event.title }}</h3>
          <p>{{ formatDate(event.start_time) }}</p>
          <p>{{ event.location }}</p>
        </div>
        <div v-if="isAdmin" class="card-actions">
          <button
            class="edit-btn"
            @click.stop="startEdit(event)"
          >编辑</button>
          <button
            class="delete-btn"
            @click.stop="deleteEventItem(event)"
          >删除</button>
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
  sale_start_time: '',
  start_time: '',
  limit_one_ticket_per_user: false
})
const imageFile = ref(null)
const seatMapFile = ref(null)
const seatMapPreview = ref(null)
const ticketTypes = ref([])
const newTicket = ref({ seat_type: '', price: 0, available_qty: 0 })
const isAdmin = localStorage.getItem('username') === 'admin'
const editingId = ref(null)
const selectedEventId = ref(null)

onMounted(loadEvents)

async function loadEvents() {
  const token = localStorage.getItem('token')
  const res = await axios.get('/events', {
    headers: { Authorization: `Bearer ${token}` }
  })
  events.value = res.data
}

function select(event) {
  selectedEventId.value = event?.id ?? null
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

function addTicket() {
  if (!newTicket.value.seat_type) return
  ticketTypes.value.push({ ...newTicket.value })
  newTicket.value = { seat_type: '', price: 0, available_qty: 0 }
}

function removeTicket(index) {
  if (index < 0 || index >= ticketTypes.value.length) return
  ticketTypes.value.splice(index, 1)
}

function formatDate(str) {
  return new Date(str + 'Z').toLocaleString()
}

async function createEvent() {
  const token = localStorage.getItem('token')
  const fd = new FormData()
  fd.append('title', form.value.title)
  fd.append('organizer', form.value.organizer)
  fd.append('location', form.value.location)
  fd.append('sale_start_time', new Date(form.value.sale_start_time).toISOString())
  fd.append('start_time', new Date(form.value.start_time).toISOString())
  fd.append('limit_one_ticket_per_user', form.value.limit_one_ticket_per_user ? 'true' : 'false')
  if (imageFile.value) {
    fd.append('image', imageFile.value)
  }
  if (seatMapFile.value) {
    fd.append('seat_map', seatMapFile.value)
  }
  fd.append('ticket_types', JSON.stringify(ticketTypes.value))
  const res = await axios.post('/events', fd, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    }
  })
  events.value.push(res.data)
  form.value = {
    title: '',
    organizer: '',
    location: '',
    sale_start_time: '',
    start_time: '',
    limit_one_ticket_per_user: false
  }
  imageFile.value = null
  seatMapFile.value = null
  seatMapPreview.value = null
  ticketTypes.value = []
}

function toLocalInput(str) {
  if (!str) return ''
  const d = new Date(str + 'Z')
  const offset = d.getTimezoneOffset()
  const local = new Date(d.getTime() - offset * 60000)
  return local.toISOString().slice(0, 16)
}

function startEdit(event) {
  editingId.value = event.id
  form.value = {
    title: event.title || '',
    organizer: event.organizer || '',
    location: event.location || '',
    sale_start_time: toLocalInput(event.sale_start_time),
    start_time: toLocalInput(event.start_time),
    limit_one_ticket_per_user: !!event.limit_one_ticket_per_user,
  }
  ticketTypes.value = event.ticket_types.map(t => ({
    seat_type: t.seat_type,
    price: t.price,
    available_qty: t.available_qty
  }))
  seatMapPreview.value = event.seat_map_url || null
  imageFile.value = null
  seatMapFile.value = null
}

async function deleteEventItem(event) {
  if (!event || !confirm(`确定要删除活动 ${event.title} 吗？`)) {
    return
  }
  const token = localStorage.getItem('token')
  try {
    await axios.delete(`/events/${event.id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    events.value = events.value.filter((e) => e.id !== event.id)
    if (editingId.value === event.id) {
      cancelEdit()
    }
    if (selectedEventId.value === event.id) {
      selectedEventId.value = null
      emit('select-event', null)
    }
  } catch (error) {
    alert(error.response?.data?.detail ?? '删除活动失败')
  }
}

async function updateEvent() {
  if (!editingId.value) return
  const token = localStorage.getItem('token')
  const fd = new FormData()
  fd.append('title', form.value.title)
  fd.append('organizer', form.value.organizer)
  fd.append('location', form.value.location)
  fd.append('sale_start_time', new Date(form.value.sale_start_time).toISOString())
  fd.append('start_time', new Date(form.value.start_time).toISOString())
  fd.append('limit_one_ticket_per_user', form.value.limit_one_ticket_per_user ? 'true' : 'false')
  fd.append('ticket_types', JSON.stringify(ticketTypes.value))
  if (form.value.description) fd.append('description', form.value.description)
  if (imageFile.value) fd.append('image', imageFile.value)
  if (seatMapFile.value) fd.append('seat_map', seatMapFile.value)
  const res = await axios.put(`/events/${editingId.value}`, fd, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    }
  })
  const idx = events.value.findIndex(e => e.id === editingId.value)
  if (idx >= 0) events.value[idx] = res.data
  cancelEdit()
}

function cancelEdit() {
  editingId.value = null
  form.value = {
    title: '',
    organizer: '',
    location: '',
    sale_start_time: '',
    start_time: '',
    limit_one_ticket_per_user: false
  }
  imageFile.value = null
  seatMapFile.value = null
  seatMapPreview.value = null
  ticketTypes.value = []
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
.create-form .field {
  flex: 1 1 200px;
  display: flex;
  flex-direction: column;
}
.create-form label {
  font-size: 0.85rem;
  margin-bottom: 0.2rem;
}
.create-form input {
  padding: 0.3rem;
  border: 1px solid #ccc;
  border-radius: 0.3rem;
}
.create-form button {
  background: #4F46E5;
  color: #fff;
  border: none;
  border-radius: 0.5rem;
  padding: 0.4rem 0.8rem;
  cursor: pointer;
}
.field.field-checkbox {
  flex: 1 1 100%;
  padding: 0.4rem 0;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
}

.checkbox-label input {
  width: auto;
}

.checkbox-hint {
  margin-top: 0.25rem;
  font-size: 0.8rem;
  color: #6B7280;
}
.block-form {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
  align-items: center;
}
.block-form label {
  display: flex;
  flex-direction: column;
  font-size: 0.85rem;
}
.block-form input {
  padding: 0.3rem;
  border: 1px solid #ccc;
  border-radius: 0.3rem;
}
.ticket-editor {
  width: 100%;
  border: 1px solid #E5E7EB;
  border-radius: 0.5rem;
  margin-top: 0.5rem;
  overflow: hidden;
}

.ticket-editor-row {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr 0.8fr auto;
  gap: 0.5rem;
  padding: 0.5rem;
  align-items: center;
}

.ticket-editor-header {
  background: #F9FAFB;
  font-weight: 600;
}

.ticket-editor-row input {
  padding: 0.3rem;
  border: 1px solid #D1D5DB;
  border-radius: 0.3rem;
}

.ticket-editor-actions {
  text-align: center;
}

.remove-ticket-btn {
  background: #DC2626;
  color: #fff;
  border: none;
  border-radius: 0.3rem;
  padding: 0.3rem 0.6rem;
  cursor: pointer;
}

.remove-ticket-btn:hover {
  background: #B91C1C;
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
.card-actions {
  display: flex;
  gap: 0.5rem;
  margin: 0.5rem;
}

.card-actions button {
  flex: 1 1 auto;
  padding: 0.3rem 0.6rem;
  border: none;
  border-radius: 0.3rem;
  color: #fff;
  cursor: pointer;
}

.card-actions .edit-btn {
  background: #4F46E5;
}

.card-actions .edit-btn:hover {
  background: #4338ca;
}

.card-actions .delete-btn {
  background: #dc2626;
}

.card-actions .delete-btn:hover {
  background: #b91c1c;
}
</style>

