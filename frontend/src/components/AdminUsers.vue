<template>
  <div class="admin">
    <h2>账户管理</h2>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>用户名</th>
          <th>水晶能量币</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.id">
          <td>{{ u.id }}</td>
          <td>{{ u.username }}</td>
          <td>{{ u.energy_coins }}</td>
          <td>
            <button @click="modify(u)">修改</button>
          </td>
        </tr>
      </tbody>
    </table>
    <button @click="$emit('close')">返回</button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const users = ref([])

onMounted(loadUsers)

async function loadUsers() {
  const token = localStorage.getItem('token')
  const res = await axios.get('/admin/users', {
    headers: { Authorization: `Bearer ${token}` }
  })
  users.value = res.data
}

async function modify(user) {
  const val = prompt('请输入新的能量币数量', user.energy_coins)
  const newCoins = parseInt(val)
  if (isNaN(newCoins)) return
  const token = localStorage.getItem('token')
  const res = await axios.put(`/admin/users/${user.id}/coins`, {
    energy_coins: newCoins
  }, {
    headers: { Authorization: `Bearer ${token}` }
  })
  user.energy_coins = res.data.energy_coins
  await axios.post(`/admin/users/${user.id}/reset_password`, {}, {
    headers: { Authorization: `Bearer ${token}` }
  })
  alert('已更新能量币并重置密码为123456')
}
</script>

<style scoped>
.admin {
  background: #fff;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-top: 1rem;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
}
th, td {
  border: 1px solid #ccc;
  padding: 0.5rem;
  text-align: center;
}
button {
  padding: 0.3rem 0.6rem;
  margin: 0 0.2rem;
  border: none;
  border-radius: 0.3rem;
  background: #4F46E5;
  color: #fff;
  cursor: pointer;
}
</style>
