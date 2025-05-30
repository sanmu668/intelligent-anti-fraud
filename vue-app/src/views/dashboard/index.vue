<template>
  <div class="dashboard">
    <!-- 加载状态 -->
    <el-loading v-if="dashboardStore.loading" :fullscreen="true" text="加载中..." />
    
    <!-- 错误提示 -->
    <el-alert
      v-if="dashboardStore.error"
      :title="dashboardStore.error"
      type="error"
      :closable="false"
      show-icon
      style="margin-bottom: 20px;"
    />

    <el-row :gutter="20">
      <!-- 统计卡片 -->
      <el-col :span="6" v-for="(item, index) in dashboardStore.statistics" :key="index">
        <div class="stat-card">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>{{ item.title }}</span>
                <el-tag v-if="item.title !== '识别准确率' && item.title !== '待处理预警'" :type="item.type" effect="dark" size="small">
                  {{ item.change }}%
                </el-tag>
              </div>
            </template>
            <div class="card-content">
              <h2>{{ item.value }}</h2>
              <p>{{ item.description }}</p>
            </div>
          </el-card>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <!-- 风险趋势图 -->
      <el-col :span="16">
        <div class="analysis-card">
          <div class="card-title">风险趋势分析</div>
          <div class="chart-container" ref="riskTrendChart"></div>
        </div>
      </el-col>
      
      <!-- 风险分布图 -->
      <el-col :span="8">
        <div class="analysis-card">
          <div class="card-title">风险类型分布</div>
          <div class="chart-container small" ref="riskDistributionChart"></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <!-- 实时监控 -->
      <el-col :span="12">
        <div class="analysis-card">
          <div class="card-title">
            实时交易监控
            <el-tag type="success" size="small" style="margin-left: 10px">实时更新</el-tag>
          </div>
          <div class="realtime-monitor">
            <el-table :data="dashboardStore.realtimeTransactions" style="width: 100%" v-loading="dashboardStore.loading" height="400">
              <el-table-column prop="timestamp" label="时间" width="180">
                <template #default="scope">
                  {{ new Date(scope.row.timestamp).toLocaleString() }}
                </template>
              </el-table-column>
              <el-table-column prop="amount" label="金额" width="120">
                <template #default="scope">
                  ¥{{ scope.row.amount.toLocaleString() }}
                </template>
              </el-table-column>
              <el-table-column prop="risk_score" label="风险评分" width="100">
                <template #default="scope">
                  <el-tag :type="getRiskLevelType(scope.row.risk_score)">
                    {{ (scope.row.risk_score * 100).toFixed(0) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="risk_type" label="风险类型" />
            </el-table>
          </div>
        </div>
      </el-col>
      
      <!-- 预警信息 -->
      <el-col :span="12">
        <div class="analysis-card">
          <div class="card-title">
            最新预警信息
            <el-tag type="danger" size="small" style="margin-left: 10px">需要处理</el-tag>
          </div>
          <div class="alert-list">
            <el-table :data="dashboardStore.alertList" style="width: 100%" v-loading="dashboardStore.loading" height="400">
              <el-table-column prop="timestamp" label="时间" width="180">
                <template #default="scope">
                  {{ new Date(scope.row.timestamp).toLocaleString() }}
                </template>
              </el-table-column>
              <el-table-column prop="type" label="类型" width="120">
                <template #default="scope">
                  <el-tag :type="scope.row.risk_level === 'high' ? 'danger' : 'warning'">
                    {{ scope.row.type }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="description" label="描述" />
              <el-table-column label="操作" width="100">
                <template #default="scope">
                  <el-button 
                    type="text" 
                    size="small"
                    @click="handleAlertAction(scope.row)"
                  >
                    处理
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, onActivated } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { useDashboardStore } from '@/store/dashboard'

// 获取仪表盘 store
const dashboardStore = useDashboardStore()

// 图表DOM引用
const riskTrendChart = ref<HTMLElement | null>(null)
const riskDistributionChart = ref<HTMLElement | null>(null)

// 图表实例
let trendChartInstance: echarts.ECharts | null = null
let distributionChartInstance: echarts.ECharts | null = null

// 风险等级判断函数
const getRiskLevelType = (score: number): string => {
  if (score > 0.7) return 'danger'
  if (score > 0.5) return 'warning'
  return 'success'
}

// 处理预警操作
const handleAlertAction = (alert: any) => {
  ElMessage({
    message: `正在处理预警: ${alert.type}`,
    type: 'success'
  })
}

// 初始化图表
const initCharts = () => {
  try {
    if (riskTrendChart.value) {
      trendChartInstance = echarts.init(riskTrendChart.value)
    }
    if (riskDistributionChart.value) {
      distributionChartInstance = echarts.init(riskDistributionChart.value)
    }
  } catch (e) {
    console.error('Failed to initialize charts:', e)
    ElMessage.error('初始化图表失败')
  }
}

// 更新趋势图表
const updateTrendChart = () => {
  if (trendChartInstance && dashboardStore.trends) {
      const option = {
        title: { text: '' },
        tooltip: { 
          trigger: 'axis',
          axisPointer: {
            type: 'cross',
            label: {
              backgroundColor: '#6a7985'
            }
          }
        },
        legend: {
          data: ['高风险交易', '可疑行为', '预警总量']
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: [
          {
            type: 'category',
            boundaryGap: false,
          data: dashboardStore.trends.xAxis
          }
        ],
        yAxis: [
          {
            type: 'value'
          }
        ],
      series: dashboardStore.trends.series
      }
      trendChartInstance.setOption(option)
  }
}

// 更新风险分布图表
const updateDistributionChart = () => {
  if (distributionChartInstance && dashboardStore.riskDistribution) {
      const option = {
        tooltip: {
          trigger: 'item',
          formatter: '{a} <br/>{b}: {c}%'
        },
        legend: {
          orient: 'vertical',
          left: 10,
        data: dashboardStore.riskDistribution.labels
        },
        series: [
          {
            name: '风险类型',
            type: 'pie',
            radius: ['50%', '70%'],
            avoidLabelOverlap: false,
            label: {
              show: true,
              position: 'outside',
              formatter: '{b}: {d}%'
            },
            emphasis: {
              label: {
                show: true,
                fontSize: '16',
                fontWeight: 'bold'
              }
            },
            labelLine: {
              show: true
            },
          data: dashboardStore.riskDistribution.labels.map((label: string, index: number) => ({
            value: dashboardStore.riskDistribution.data[index],
              name: label
            }))
          }
        ]
      }
      distributionChartInstance.setOption(option)
  }
}

// 处理窗口大小变化
const handleResize = () => {
  trendChartInstance?.resize()
  distributionChartInstance?.resize()
}

// 更新所有图表
const updateCharts = () => {
  updateTrendChart()
  updateDistributionChart()
}

// 定时刷新
let refreshInterval: number | null = null

const startRefreshInterval = () => {
  // 清除旧的定时器
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  
  // 设置新的定时器, 30秒刷新一次数据
  refreshInterval = window.setInterval(async () => {
    await dashboardStore.refreshAllData()
    updateCharts()
  }, 30000)
}

// 组件初始化
const init = async () => {
    // 初始化图表
  initCharts()
    
    // 添加窗口大小变化监听
  window.addEventListener('resize', handleResize)
  
  // 如果数据过期或没有数据, 则加载最新数据
  if (dashboardStore.isDataStale() || dashboardStore.statistics.length === 0) {
    await dashboardStore.refreshAllData()
  }
  
  // 更新图表
  updateCharts()
    
    // 启动定时刷新
  startRefreshInterval()
}

// 生命周期钩子
onMounted(() => {
  init()
})

// 当从缓存中重新激活时调用
onActivated(() => {
  // 重新绑定事件监听
  window.addEventListener('resize', handleResize)
  
  // 如果数据过期，刷新数据
  if (dashboardStore.isDataStale()) {
    dashboardStore.refreshAllData().then(updateCharts)
  }
  
  // 恢复定时刷新
  startRefreshInterval()
  
  // 重新初始化可能已销毁的图表
  initCharts()
  updateCharts()
})

// 当组件卸载或被缓存前调用
onUnmounted(() => {
  // 清理资源
  window.removeEventListener('resize', handleResize)
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
  trendChartInstance?.dispose()
  distributionChartInstance?.dispose()
})
</script>

<style lang="scss" scoped>
.dashboard {
  padding: 20px;
  min-height: 100vh;
  background-color: #f5f7fa;
  
  .stat-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .card-content {
      text-align: center;
      
      h2 {
        font-size: 24px;
        color: #303133;
        margin: 10px 0;
      }
      
      p {
        font-size: 14px;
        color: #909399;
        margin: 0;
      }
    }
  }
  
  .chart-row {
    margin-bottom: 20px;
  }
  
  .analysis-card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
    
    .card-title {
      font-size: 16px;
      font-weight: 500;
      color: #303133;
      margin-bottom: 20px;
    }
    
    .chart-container {
      height: 400px;
      
      &.small {
        height: 300px;
      }
    }
  }
}

.realtime-monitor, .alert-list {
  height: 400px;
  overflow: hidden;
}

.el-table {
  margin-top: 10px;
  
  :deep(.el-table__body-wrapper) {
    overflow-y: auto;
  }
}

.card-title {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
}
</style> 