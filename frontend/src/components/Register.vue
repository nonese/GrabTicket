<template>
  <div class="login">
    <h2>注册</h2>
    <form @submit.prevent="register">
      <label>
        用户名
        <input v-model="username" placeholder="请输入用户名" required />
      </label>
      <label>
        密码
        <input v-model="password" type="password" placeholder="请输入密码" required />
      </label>
      <label>
        能量币
        <input v-model.number="energyCoins" type="number" placeholder="请输入能量币数量" required />
      </label>
      <button type="submit">注册</button>
    </form>
    <p v-if="error" class="error">{{ error }}</p>
    <button class="back" @click="$emit('cancel')">返回登录</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const emit = defineEmits(['registered', 'cancel'])

const username = ref('')
const password = ref('')
const energyCoins = ref(0)
const error = ref('')

async function register() {
  try {
    await axios.post('/auth/register', {
      username: username.value,
      password: password.value,
      energy_coins: energyCoins.value
    })
    emit('registered')
  } catch (e) {
    error.value = e.response?.data?.detail || '注册失败'
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
.back {
  margin-top: 0.5rem;
}
.error {
  color: red;
}
</style>
