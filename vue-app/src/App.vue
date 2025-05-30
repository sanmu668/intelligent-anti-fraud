<template>
  <div class="app-container theme-light-blue">
    <el-container>
      <el-aside width="200px">
        <sidebar />
      </el-aside>
      <el-container>
        <el-header>
          <navbar />
        </el-header>
        <el-main>
          <router-view v-slot="{ Component, route }">
            <transition name="fade" mode="out-in">
              <keep-alive :include="cachedViews">
                <component :is="Component" :key="route.path" />
              </keep-alive>
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import Navbar from '@/components/layout/Navbar.vue'

// List of component names that should be cached with keep-alive
// These should match the component names used in your routes
const cachedViews = ref([
  'GraphAnalysis',     // 图谱分析 (graph-analysis)
  'MonitorAlerts',     // 预警中心 (monitor/alerts)
  'GroupAnalysis'      // 行为分析 (group/analysis)
])
</script>

<style lang="scss" scoped>
.app-container {
  height: 100vh;
  
  .el-container {
    height: 100%;
  }
  
  .el-header {
    height: 60px;
    line-height: 60px;
    padding: 0 20px;
  }
  
  .el-aside {
    width: 200px !important;
  }
  
  .el-main {
    padding: 20px;
    overflow-y: auto;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style> 