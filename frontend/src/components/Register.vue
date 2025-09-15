<template>
  <div class="login">
    <h2>注册</h2>
    <form @submit.prevent="register">
      <input v-model="username" placeholder="用户名" required />
      <input v-model="password" type="password" placeholder="密码" required />
      <input v-model.number="energyCoins" type="number" placeholder="水晶能量币" required />
      <button type="submit">注册</button>
    </form>
    <p v-if="error" class="error">{{ error }}</p>
    <button @click="$emit('cancel')">返回登录</button>
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
    error.value = '注册失败'
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
