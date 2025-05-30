<template>
  <div class="placeholder">
    <el-card>
      <el-empty description="团伙分析功能已下线" />
      <div class="placeholder-message">
        <p>此功能已被移除。请联系管理员获取更多信息。</p>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
// Simplified component with no gang detection functionality
</script>

<style scoped>
.placeholder {
  padding: 20px;
}

.placeholder-message {
  text-align: center;
  margin-top: 20px;
  color: #909399;
}
</style>