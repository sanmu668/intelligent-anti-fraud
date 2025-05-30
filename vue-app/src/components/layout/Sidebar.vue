<template>
  <div class="sidebar">
    <el-menu
      :default-active="activeMenu"
      class="el-menu-vertical"
      :collapse="isCollapse"
      background-color="transparent"
      text-color="#2c3e50"
      active-text-color="#409EFF"
      router
    >
      <el-menu-item index="/dashboard">
        <el-icon><DataLine /></el-icon>
        <template #title>仪表盘</template>
      </el-menu-item>
      
      <el-menu-item index="/graph-analysis">
        <el-icon><Connection /></el-icon>
        <template #title>图谱分析</template>
      </el-menu-item>
      
      <el-menu-item index="/monitor/realtime">
        <el-icon><Monitor /></el-icon>
        <template #title>实时监控</template>
      </el-menu-item>
      
      <el-menu-item index="/monitor/alerts">
        <el-icon><Bell /></el-icon>
        <template #title>预警中心</template>
      </el-menu-item>
      
      <el-menu-item index="/group/analysis">
        <el-icon><Share /></el-icon>
        <template #title>行为分析</template>
      </el-menu-item>

      <el-menu-item index="/chat">
        <el-icon><ChatDotRound /></el-icon>
        <span>智能客服</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isCollapse = ref(false)

const activeMenu = computed(() => {
  return route.path
})
</script>

<style lang="scss" scoped>
.sidebar {
  height: 100%;
  border-right: 1px solid #e6e6e6;
  
  .el-menu {
    border-right: none;
    
    &:not(.el-menu--collapse) {
      width: 200px;
    }
  }
  
  .el-menu-item {
    &:hover {
      background-color: #ecf5ff;
    }
    
    &.is-active {
      background-color: #ecf5ff;
      
      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background-color: #409EFF;
      }
    }
  }
}
</style> 