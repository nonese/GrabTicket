<template>
  <div class="container">
    <Login v-if="!token" @logged-in="token = $event" />
    <div v-else>
      <EventList @select-event="selectEvent" />
      <EventDetail v-if="currentEvent" :event="currentEvent" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Login from './components/Login.vue'
import EventList from './components/EventList.vue'
import EventDetail from './components/EventDetail.vue'

const token = ref(localStorage.getItem('token'))
const currentEvent = ref(null)

function selectEvent(event) {
  currentEvent.value = event
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
</style>
