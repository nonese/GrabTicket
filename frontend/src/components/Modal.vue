<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="modal">
      <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal {
  background: #fff;
  padding: 1rem;
  border-radius: 0.5rem;
  min-width: 200px;
}
</style>

