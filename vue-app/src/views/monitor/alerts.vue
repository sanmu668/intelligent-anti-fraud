<template>
  <div class="alerts-view">
    <!-- 搜索过滤器 -->
    <div class="filter-section">
      <el-form :inline="true" :model="filterForm" @submit.prevent="handleSearch">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="filterForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            :shortcuts="dateShortcuts"
          />
        </el-form-item>
        <el-form-item label="预警类型">
          <el-select v-model="filterForm.alertType" placeholder="请选择">
            <el-option label="全部" value="" />
            <el-option label="交易风险" value="transaction" />
            <el-option label="行为异常" value="behavior" />
            <el-option label="团伙识别" value="group" />
          </el-select>
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="filterForm.riskLevel" placeholder="请选择">
            <el-option label="全部" value="" />
            <el-option label="高风险" value="high" />
            <el-option label="中风险" value="medium" />
            <el-option label="低风险" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理状态">
          <el-select v-model="filterForm.status" placeholder="请选择">
            <el-option label="全部" value="" />
            <el-option label="未处理" value="pending" />
            <el-option label="处理中" value="processing" />
            <el-option label="已处理" value="resolved" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 预警列表 -->
    <div class="alerts-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <h3>预警列表</h3>
              <el-tag type="danger">{{ alertsStore.totalAlerts }} 个预警</el-tag>
            </div>
            <div class="header-right">
              <el-button type="primary" @click="handleBatchProcess" :disabled="!selectedAlerts.length">
                批量处理
              </el-button>
              <el-button @click="handleExport" :disabled="!alertsStore.alerts.length">导出</el-button>
              <el-button @click="handleRefresh">刷新</el-button>
            </div>
          </div>
        </template>

        <el-table
          :data="alertsStore.alerts"
          style="width: 100%"
          @selection-change="handleSelectionChange"
          v-loading="alertsStore.loading"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="time" label="时间" width="180" sortable />
          <el-table-column prop="type" label="预警类型" width="120">
            <template #default="scope">
              <el-tag :type="getAlertTypeTag(scope.row.type)">
                {{ getAlertTypeLabel(scope.row.type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="预警标题" min-width="200" />
          <el-table-column prop="riskLevel" label="风险等级" width="100">
            <template #default="scope">
              <el-tag :type="getRiskLevelTag(scope.row.riskLevel)">
                {{ getRiskLevelLabel(scope.row.riskLevel) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="getStatusTag(scope.row.status)">
                {{ getStatusLabel(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="handler" label="处理人" width="120" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button
                type="primary"
                link
                @click="handleAlertDetail(scope.row)"
              >
                详情
              </el-button>
              <el-button
                type="success"
                link
                @click="handleProcess(scope.row)"
                v-if="scope.row.status === 'pending'"
              >
                处理
              </el-button>
              <el-button
                type="info"
                link
                @click="handleHistory(scope.row)"
              >
                历史
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="alertsStore.totalAlerts"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </el-card>
    </div>

    <!-- 预警详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="预警详情"
      width="60%"
      destroy-on-close
    >
      <alert-detail
        v-if="selectedAlert"
        :alert="selectedAlert"
        @process="handleDetailProcess"
      />
    </el-dialog>

    <!-- 处理对话框 -->
    <el-dialog
      v-model="processDialogVisible"
      title="处理预警"
      width="50%"
      destroy-on-close
    >
      <el-form :model="processForm" label-width="100px">
        <el-form-item label="处理方式">
          <el-select v-model="processForm.method" placeholder="请选择处理方式">
            <el-option label="确认处理" value="confirm" />
            <el-option label="标记误报" value="false_positive" />
            <el-option label="转交处理" value="transfer" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理说明">
          <el-input
            v-model="processForm.description"
            type="textarea"
            rows="4"
            placeholder="请输入处理说明"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="processDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitProcess">
            确认
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onActivated } from 'vue'
import { ElMessage } from 'element-plus'
import { useAlertsStore } from '@/store/alerts'

// 获取 alerts store
const alertsStore = useAlertsStore()

// 日期快捷选项
const dateShortcuts = [
  {
    text: '最近一周',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
      return [start, end]
    },
  },
  {
    text: '最近一月',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
      return [start, end]
    },
  },
  {
    text: '最近三月',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 90)
      return [start, end]
    },
  }
]

// 过滤表单
const filterForm = ref({
  dateRange: [] as string[],
  alertType: '',
  riskLevel: '',
  status: '',
  startDate: '',
  endDate: ''
})

// 分页参数
const currentPage = ref(1)
const pageSize = ref(20)

// 选中的预警
const selectedAlerts = ref<any[]>([])

// 对话框控制
const detailDialogVisible = ref(false)
const processDialogVisible = ref(false)
const selectedAlert = ref<any | null>(null)

// 处理表单
const processForm = ref({
  method: '',
  description: ''
})

// 获取标签类型和标签文本
const getAlertTypeTag = (type: string) => {
  const types: { [key: string]: string } = {
    'transaction': 'danger',
    'behavior': 'warning',
    'group': 'info'
  }
  return types[type] || 'info'
}

const getAlertTypeLabel = (type: string) => {
  const labels: { [key: string]: string } = {
    'transaction': '交易风险',
    'behavior': '行为异常',
    'group': '团伙识别'
  }
  return labels[type] || type
}

const getRiskLevelTag = (level: string) => {
  const levels: { [key: string]: string } = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'info'
  }
  return levels[level] || 'info'
}

const getRiskLevelLabel = (level: string) => {
  const labels: { [key: string]: string } = {
    'high': '高风险',
    'medium': '中风险',
    'low': '低风险'
  }
  return labels[level] || level
}

const getStatusTag = (status: string) => {
  const statuses: { [key: string]: string } = {
    'pending': 'danger',
    'processing': 'warning',
    'resolved': 'success'
  }
  return statuses[status] || 'info'
}

const getStatusLabel = (status: string) => {
  const labels: { [key: string]: string } = {
    'pending': '未处理',
    'processing': '处理中',
    'resolved': '已处理'
  }
  return labels[status] || status
}

// 加载预警数据
const loadAlerts = async () => {
  // 设置 store 中的分页和过滤参数
  alertsStore.setCurrentPage(currentPage.value);
  alertsStore.setPageSize(pageSize.value);
  
  // 转换日期范围格式 - 修复日期范围参数传递问题
  const params = { ...filterForm.value };
  
  // 如果有日期范围，则正确格式化为字符串形式供API使用
  if (params.dateRange && Array.isArray(params.dateRange) && params.dateRange.length === 2) {
    params.startDate = params.dateRange[0];
    params.endDate = params.dateRange[1];
  }
  
  // 创建新的API参数对象，不包含dateRange
  const apiParams = {
    alertType: params.alertType,
    riskLevel: params.riskLevel,
    status: params.status,
    startDate: params.startDate,
    endDate: params.endDate
  };
  
  alertsStore.setFilterParams(apiParams);
  
  try {
    await alertsStore.fetchAlerts();
  } catch (error) {
    console.error('Failed to load alerts:', error);
  }
}

// 事件处理函数
const handleSearch = () => {
  currentPage.value = 1;
  loadAlerts();
}

const handleReset = () => {
  filterForm.value = {
    dateRange: [],
    alertType: '',
    riskLevel: '',
    status: '',
    startDate: '',
    endDate: ''
  };
  
  alertsStore.resetFilters();
  currentPage.value = 1;
  pageSize.value = 20;
  loadAlerts();
}

const handleRefresh = () => {
  alertsStore.clearCache();
  loadAlerts();
}

const handleSelectionChange = (selection: any[]) => {
  selectedAlerts.value = selection;
}

const handleSizeChange = (size: number) => {
  pageSize.value = size;
  alertsStore.setPageSize(size);
  loadAlerts();
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page;
  alertsStore.setCurrentPage(page);
  loadAlerts();
}

const handleAlertDetail = (alert: any) => {
  selectedAlert.value = alert;
  detailDialogVisible.value = true;
}

const handleProcess = (alert: any) => {
  selectedAlert.value = alert;
  processDialogVisible.value = true;
}

const handleHistory = (alert: any) => {
  ElMessage.info('历史记录功能开发中');
}

const handleBatchProcess = async () => {
  if (selectedAlerts.value.length === 0) {
    ElMessage.warning('请选择要处理的预警');
    return;
  }
  
  try {
    const result = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/alerts/batch-process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        alertIds: selectedAlerts.value.map(alert => alert.id),
        method: 'batch',
        description: '批量处理预警',
        handler: 'Admin'
      })
    });
    
    const data = await result.json();
    
    if (data.success) {
      ElMessage.success(`成功处理 ${selectedAlerts.value.length} 条预警`);
      loadAlerts();
    }
  } catch (error) {
    console.error('Failed to batch process alerts:', error);
    ElMessage.error('批量处理预警失败');
  }
}

const handleExport = () => {
  if (alertsStore.alerts.length === 0) {
    ElMessage.warning('没有可导出的数据');
    return;
  }
  
  ElMessage.info('导出功能开发中');
}

const handleDetailProcess = (alert: any) => {
  processDialogVisible.value = true;
}

const submitProcess = async () => {
  if (!selectedAlert.value) return;
  
  try {
    const success = await alertsStore.updateAlertStatus(
      selectedAlert.value.id,
      processForm.value.method,
      processForm.value.description
    );
    
    if (success) {
      processDialogVisible.value = false;
      
      // 重置表单
      processForm.value = {
        method: '',
        description: ''
      };
      
      // 重新加载数据
      loadAlerts();
    }
  } catch (error) {
    console.error('Failed to process alert:', error);
  }
}

// 初始化
const init = async () => {
  // 同步本地分页状态到 store
  alertsStore.setCurrentPage(currentPage.value);
  alertsStore.setPageSize(pageSize.value);
  
  // 加载预警数据
  await loadAlerts();
}

// 生命周期钩子
onMounted(() => {
  init();
})

// 当从缓存中重新激活时调用
onActivated(() => {
  // 如果过滤条件改变，或分页状态不同步，则重新加载
  if (
    JSON.stringify(filterForm.value) !== JSON.stringify(alertsStore.filterParams) ||
    currentPage.value !== alertsStore.currentPage ||
    pageSize.value !== alertsStore.pageSize
  ) {
    loadAlerts();
  }
})
</script>

<style lang="scss" scoped>
.alerts-view {
  padding: 20px;
  
  .filter-section {
    background: white;
    padding: 20px;
    border-radius: 4px;
    margin-bottom: 20px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  }
  
  .alerts-section {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .header-left {
        display: flex;
        align-items: center;
        gap: 12px;
        
        h3 {
          margin: 0;
        }
      }
    }
    
    .pagination-container {
      margin-top: 20px;
      display: flex;
      justify-content: flex-end;
    }
  }
}
</style> 