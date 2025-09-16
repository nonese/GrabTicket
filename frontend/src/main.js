import { createApp } from 'vue'
import axios from 'axios'
import App from './App.vue'

const apiBase = import.meta.env.VITE_API_BASE?.trim()
if (apiBase) {
  axios.defaults.baseURL = apiBase.replace(/\/$/, '')
}

createApp(App).mount('#app')
