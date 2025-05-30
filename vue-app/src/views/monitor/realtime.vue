<template>
  <div class="realtime-monitor">
    <!-- 顶部统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6" v-for="(stat, index) in statistics" :key="index">
        <el-card shadow="hover" :body-style="{ padding: '20px' }">
          <div class="stat-item">
            <div class="icon-wrapper" :class="stat.type">
              <el-icon><component :is="stat.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="label">{{ stat.label }}</div>
              <div class="value">{{ stat.value }}</div>
              <div class="trend" :class="parseFloat(stat.trend) > 0 ? 'up' : 'down'">
                {{ parseFloat(stat.trend) > 0 ? '+' : '' }}{{ stat.trend }}%
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 主要内容区 -->
    <el-row :gutter="20" class="main-content">
      <!-- 左侧实时交易流 -->
      <el-col :span="16">
        <el-card class="transaction-flow">
          <template #header>
            <div class="card-header">
              <span>实时交易流</span>
              <div class="header-controls">
                <el-switch
                  v-model="autoRefresh"
                  active-text="自动刷新"
                  @change="handleAutoRefreshChange"
                />
              </div>
            </div>
          </template>
          <div class="flow-content">
            <el-table
              :data="alertsStore.transactions"
              style="width: 100%"
              :max-height="500"
              v-loading="alertsStore.loading"
            >
              <el-table-column prop="time" label="时间" width="180" />
              <el-table-column prop="type" label="类型" width="120">
                <template #default="scope">
                  <el-tag :type="getTransactionTypeTag(scope.row.type)">
                    {{ scope.row.type }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="amount" label="金额" width="150">
                <template #default="scope">
                  ¥{{ scope.row.amount.toLocaleString() }}
                </template>
              </el-table-column>
              <el-table-column prop="source" label="来源账户" width="180" />
              <el-table-column prop="target" label="目标账户" width="180" />
              <el-table-column prop="riskScore" label="风险评分" width="180">
                <template #default="scope">
                  <el-progress
                    :percentage="scope.row.riskScore"
                    :color="getRiskColor(scope.row.riskScore)"
                    :format="() => ''"
                  />
                  <div style="text-align: center; margin-top: 4px; font-size: 12px;">
                    {{ scope.row.riskScore.toFixed(2) }}%
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="scope">
                  <el-button
                    type="primary"
                    link
                    @click="handleDetail(scope.row)"
                  >
                    详情
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧预警面板 -->
      <el-col :span="8">
        <el-card class="alert-panel">
          <template #header>
            <div class="card-header">
              <span>实时预警</span>
              <el-tag type="danger">{{ alerts.length }} 个未处理</el-tag>
            </div>
          </template>
          <div class="alert-content">
            <el-timeline>
              <el-timeline-item
                v-for="alert in alerts"
                :key="alert.id"
                :type="alert.level"
                :timestamp="alert.time"
                :hollow="!alert.read"
              >
                <h4>{{ alert.title }}</h4>
                <p>{{ alert.description }}</p>
                <div class="alert-actions">
                  <el-button type="primary" link @click="handleAlertDetail(alert)">
                    查看详情
                  </el-button>
                  <el-button type="success" link @click="handleAlertProcess(alert)">
                    标记处理
                  </el-button>
                </div>
              </el-timeline-item>
            </el-timeline>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 交易详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="交易详情"
      width="50%"
      destroy-on-close
    >
      <transaction-detail
        v-if="selectedTransaction"
        :transaction="selectedTransaction"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, onActivated } from 'vue'
import { Monitor, Warning, Money, Share } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAlertsStore } from '@/store/alerts'

// 获取交易和预警 store
const alertsStore = useAlertsStore()

interface Alert {
  id: string
  time: string
  title: string
  description: string
  level: 'info' | 'warning' | 'error'
  read: boolean
}

interface Statistics {
  label: string
  value: string
  trend: string
  type: string
  icon: any
}

// 轮询相关
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
const autoRefresh = ref(true)
const pollingInterval = ref<number | null>(null)
const POLLING_DELAY = 5000 // 5秒轮询一次

// 统计数据
const statistics = ref<Statistics[]>([
  {
    label: '实时交易量',
    value: '0',
    trend: '0.0',
    type: 'primary',
    icon: Monitor
  },
  {
    label: '风险交易',
    value: '0',
    trend: '0.0',
    type: 'danger',
    icon: Warning
  },
  {
    label: '交易总额',
    value: '￥0',
    trend: '0.0',
    type: 'success',
    icon: Money
  },
  {
    label: '活跃账户',
    value: '0',
    trend: '0.0',
    type: 'info',
    icon: Share
  }
])

// 预警数据
const alerts = ref<Alert[]>([])

// 状态变量
const detailDialogVisible = ref(false)
const selectedTransaction = ref<any | null>(null)

// 更新统计数据
const updateStatistics = (data: any) => {
  // 格式化值
  const formatValue = (value: number) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`
    }
    return value.toLocaleString()
  }

  // 更新统计数据
  statistics.value = [
    {
      label: '实时交易量',
      value: formatValue(data.transaction_count || 0),
      trend: `${(data.transaction_trend || 0).toFixed(1)}`,
      type: data.transaction_trend >= 0 ? 'primary' : 'danger',
      icon: Monitor
    },
    {
      label: '风险交易',
      value: formatValue(data.risk_transaction_count || 0),
      trend: `${(data.risk_transaction_trend || 0).toFixed(1)}`,
      type: data.risk_transaction_count > 0 ? 'danger' : 'success',
      icon: Warning
    },
    {
      label: '交易总额',
      value: `￥${formatValue(data.total_amount || 0)}`,
      trend: `${(data.amount_trend || 0).toFixed(1)}`,
      type: data.amount_trend >= 0 ? 'success' : 'warning',
      icon: Money
    },
    {
      label: '活跃账户',
      value: formatValue(data.active_accounts || 0),
      trend: `${(data.active_accounts_trend || 0).toFixed(1)}`,
      type: data.active_accounts_trend >= 0 ? 'info' : 'warning',
      icon: Share
    }
  ]
}

// 轮询数据
const pollData = async () => {
  try {
    // 获取统计数据
    const statsResponse = await fetch(`${API_BASE_URL}/api/monitor/statistics`)
    if (!statsResponse.ok) throw new Error('Failed to fetch statistics')
    const statsData = await statsResponse.json()
    updateStatistics(statsData)
    
    // 获取交易数据
    await alertsStore.fetchTransactions()
    
    // 获取预警数据
    const alertsResponse = await fetch(`${API_BASE_URL}/api/monitor/alerts`)
    if (!alertsResponse.ok) throw new Error('Failed to fetch alerts')
    const alertsData = await alertsResponse.json()
    
    alerts.value = alertsData.map((alert: any) => {
      const timestamp = new Date(alert.timestamp)
      
      return {
        id: alert.id || `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        time: timestamp.toLocaleString(),
        title: alert.title || '未知预警',
        description: alert.description || '无详细信息',
        level: ['info', 'warning', 'error'].includes(alert.severity) ? alert.severity : 'warning',
        read: Boolean(alert.processed)
      }
    })
  } catch (error) {
    console.error('Failed to poll data:', error)
    ElMessage.error('数据更新失败，请检查网络连接')
  }
}

// 开始轮询
const startPolling = () => {
  if (!pollingInterval.value) {
    pollData() // 立即执行一次
    pollingInterval.value = window.setInterval(pollData, POLLING_DELAY)
  }
}

// 停止轮询
const stopPolling = () => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
    pollingInterval.value = null
  }
}

// 自动刷新处理
const handleAutoRefreshChange = (value: boolean) => {
  if (value) {
    startPolling()
  } else {
    stopPolling()
  }
}

// 加载初始数据
const loadInitialData = async () => {
  try {
    alertsStore.loading = true
    await pollData()
  } catch (error) {
    console.error('Failed to load initial data:', error)
    ElMessage.error('初始数据加载失败，请检查网络连接')
  } finally {
    alertsStore.loading = false
  }
}

// 获取交易类型标签
const getTransactionTypeTag = (type: string) => {
  const types: { [key: string]: string } = {
    'TRANSFER': 'primary',
    'PAYMENT': 'success',
    'CASH_OUT': 'warning'
  }
  return types[type] || 'info'
}

// 获取风险颜色
const getRiskColor = (score: number) => {
  if (score >= 80) return '#F56C6C'      // 高风险 - 红色
  if (score >= 60) return '#E6A23C'      // 中风险 - 橙色
  return '#67C23A'                       // 低风险 - 绿色
}

// 查看交易详情
const handleDetail = (transaction: any) => {
  selectedTransaction.value = transaction
  detailDialogVisible.value = true
}

// 处理预警
const handleAlertDetail = async (alert: Alert) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/monitor/alerts/${alert.id}`)
    if (!response.ok) throw new Error('Failed to fetch alert details')
    
    const data = await response.json()
    console.log('Alert details:', data)
    
    ElMessage.info('详情查看功能开发中')
  } catch (error) {
    console.error('Failed to fetch alert details:', error)
    ElMessage.error('获取预警详情失败')
  }
}

const handleAlertProcess = async (alert: Alert) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/monitor/alerts/${alert.id}/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        handler: 'Admin'
      })
    })
    
    if (!response.ok) throw new Error('Failed to process alert')
    
    alert.read = true
    ElMessage.success('预警已标记为已处理')
    
    // 更新预警列表
    const index = alerts.value.findIndex(a => a.id === alert.id)
    if (index !== -1) {
      alerts.value[index].read = true
    }
  } catch (error) {
    console.error('Failed to process alert:', error)
    ElMessage.error('处理预警失败')
  }
}

// 生命周期钩子
onMounted(() => {
  loadInitialData()
  if (autoRefresh.value) {
    startPolling()
  }
})

onActivated(() => {
  if (autoRefresh.value && !pollingInterval.value) {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style lang="scss" scoped>
.realtime-monitor {
  padding: 20px;
  
  .stat-cards {
    margin-bottom: 20px;
    
    .stat-item {
      display: flex;
      align-items: center;
      
      .icon-wrapper {
        width: 48px;
        height: 48px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 16px;
        
        &.primary {
          background-color: #ecf5ff;
          color: #409EFF;
        }
        
        &.danger {
          background-color: #fef0f0;
          color: #F56C6C;
        }
        
        &.success {
          background-color: #f0f9eb;
          color: #67C23A;
        }
        
        &.info {
          background-color: #f4f4f5;
          color: #909399;
        }
        
        .el-icon {
          font-size: 24px;
        }
      }
      
      .stat-info {
        flex: 1;
        
        .label {
          font-size: 14px;
          color: #606266;
          margin-bottom: 4px;
        }
        
        .value {
          font-size: 24px;
          font-weight: bold;
          color: #303133;
          margin-bottom: 4px;
        }
        
        .trend {
          font-size: 12px;
          
          &.up {
            color: #67C23A;
          }
          
          &.down {
            color: #F56C6C;
          }
        }
      }
    }
  }
  
  .main-content {
    .transaction-flow, .alert-panel {
      height: calc(100vh - 280px);
      
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        
        .header-controls {
          display: flex;
          align-items: center;
          gap: 16px;
        }
      }
      
      .flow-content, .alert-content {
        height: calc(100% - 60px);
        overflow-y: auto;
      }
    }
    
    .alert-content {
      padding: 20px;
      
      .alert-actions {
        margin-top: 8px;
      }
    }
  }
}
</style> 