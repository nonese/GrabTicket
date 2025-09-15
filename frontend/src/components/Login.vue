<template>
  <div class="login">
    <h2>登录</h2>
    <form @submit.prevent="login">
      <input v-model="username" placeholder="用户名" />
      <input v-model="password" type="password" placeholder="密码" />
      <button type="submit">登录</button>
    </form>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const emit = defineEmits(['logged-in'])

const username = ref('')
const password = ref('')
const error = ref('')

async function login() {
  try {
    const form = new URLSearchParams()
    form.append('username', username.value)
    form.append('password', password.value)
    const res = await axios.post('/auth/login', form)
    localStorage.setItem('token', res.data.access_token)
    emit('logged-in', res.data.access_token)
  } catch (e) {
    error.value = '登录失败'
  }
}
</script>

<style scoped>
.login {
  max-width: 300px;
  margin: 2rem auto;
  display: flex;
  flex-direction: column;
  background: #fff;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
input {
  margin-bottom: 0.5rem;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 0.5rem;
}
button {
  padding: 0.5rem;
  cursor: pointer;
  background: #5A9AFF;
  color: #fff;
  border: none;
  border-radius: 0.5rem;
}
.error {
  color: red;
}
</style>
