<template>
  <div class="login">
    <h2>登录</h2>
    <form @submit.prevent="login">
      <label>
        用户名
        <input v-model="username" placeholder="请输入用户名" />
      </label>
      <label>
        密码
        <input v-model="password" type="password" placeholder="请输入密码" />
      </label>
      <button type="submit">登录</button>
    </form>
    <p v-if="error" class="error">{{ error }}</p>
    <p class="switch">还没有账号？<a href="#" @click.prevent="$emit('show-register')">注册</a></p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const emit = defineEmits(['logged-in', 'show-register'])

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
    localStorage.setItem('username', username.value)
    emit('logged-in', res.data.access_token)
  } catch (e) {
    if (e.response?.data?.detail) {
      error.value = e.response.data.detail
    } else if (e.response?.status === 422) {
      error.value = '请输入用户名和密码'
    } else {
      error.value = '登录失败'
    }
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
label {
  display: flex;
  flex-direction: column;
  text-align: left;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}
input {
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 0.5rem;
}
button {
  padding: 0.5rem;
  cursor: pointer;
  background: #4F46E5;
  color: #fff;
  border: none;
  border-radius: 0.5rem;
}
.error {
  color: red;
}
</style>
