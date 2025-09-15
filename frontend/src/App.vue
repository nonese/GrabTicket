<template>
  <div class="container">
    <Login
      v-if="view === 'login'"
      @logged-in="onLoggedIn"
      @show-register="view = 'register'"
    />
    <Register
      v-else-if="view === 'register'"
      @registered="view = 'login'"
      @cancel="view = 'login'"
    />
    <div v-else-if="view === 'events'">
      <button v-if="isAdmin" class="admin-btn" @click="view = 'admin'">管理账户</button>
      <EventList @select-event="selectEvent" />
      <EventDetail v-if="currentEvent" :event="currentEvent" />
    </div>
    <AdminUsers v-else-if="view === 'admin' && isAdmin" @close="view = 'events'" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import Login from './components/Login.vue'
import Register from './components/Register.vue'
import EventList from './components/EventList.vue'
import EventDetail from './components/EventDetail.vue'
import AdminUsers from './components/AdminUsers.vue'

const token = ref(localStorage.getItem('token'))
const currentEvent = ref(null)
const username = ref(localStorage.getItem('username'))
const view = ref(token.value ? 'events' : 'login')
const isAdmin = computed(() => username.value === 'admin')

function selectEvent(event) {
  currentEvent.value = event
}

function onLoggedIn(t) {
  token.value = t
  username.value = localStorage.getItem('username')
  view.value = 'events'
}
</script>

<style>
.container {
  max-width: 750px;
  margin: 0 auto;
  padding: 1.5rem;
  text-align: center;
  position: relative;
}
.admin-btn {
  position: absolute;
  right: 1rem;
  top: 1rem;
  padding: 0.3rem 0.6rem;
  border: none;
  border-radius: 0.3rem;
  background: #4F46E5;
  color: #fff;
  cursor: pointer;
}
</style>
