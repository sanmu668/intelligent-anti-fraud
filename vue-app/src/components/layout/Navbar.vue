<template>
  <div class="navbar">
    <div class="left">
      <h2>欺诈检测平台</h2>
    </div>
    <div class="right">
      <div class="user-info">
        <el-avatar :size="32" :src="userAvatar" />
        <span class="username">{{ username }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const username = ref('Admin')
const userAvatar = ref('https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png')
</script>

<style lang="scss" scoped>
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  
  .left {
    h2 {
      color: white;
      margin: 0;
      font-size: 20px;
    }
  }
  
  .right {
    .user-info {
      display: flex;
      align-items: center;
      color: white;
      
      .username {
        margin-left: 8px;
      }
    }
  }
}
</style> 