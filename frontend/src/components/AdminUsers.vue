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
            <button @click="openModify(u)">修改</button>
          </td>
        </tr>
      </tbody>
    </table>
    <button @click="$emit('close')">返回</button>

    <Modal v-if="showEditor" @close="showEditor = false">
      <h3>修改能量币</h3>
      <input type="number" v-model.number="newCoins" />
      <div class="modal-actions">
        <button @click="submitModify">保存</button>
        <button @click="showEditor = false">取消</button>
      </div>
    </Modal>

    <Modal v-if="showMessage" @close="showMessage = false">
      <p>{{ message }}</p>
      <div class="modal-actions">
        <button @click="showMessage = false">确定</button>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import Modal from './Modal.vue'

const users = ref([])
const showEditor = ref(false)
const showMessage = ref(false)
const message = ref('')
const newCoins = ref(0)
const currentUser = ref(null)

onMounted(loadUsers)

async function loadUsers() {
  const token = localStorage.getItem('token')
  const res = await axios.get('/admin/users', {
    headers: { Authorization: `Bearer ${token}` }
  })
  users.value = res.data
}

function openModify(user) {
  currentUser.value = user
  newCoins.value = user.energy_coins
  showEditor.value = true
}

async function submitModify() {
  const token = localStorage.getItem('token')
  const res = await axios.put(`/admin/users/${currentUser.value.id}/coins`, {
    energy_coins: newCoins.value
  }, {
    headers: { Authorization: `Bearer ${token}` }
  })
  currentUser.value.energy_coins = res.data.energy_coins
  await axios.post(`/admin/users/${currentUser.value.id}/reset_password`, {}, {
    headers: { Authorization: `Bearer ${token}` }
  })
  showEditor.value = false
  message.value = '已更新能量币并重置密码为123456'
  showMessage.value = true
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

.modal-actions {
  margin-top: 1rem;
}

.modal-actions button {
  margin: 0 0.3rem;
}
</style>
