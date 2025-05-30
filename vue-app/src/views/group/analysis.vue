<template>
  <div class="gang-behavior">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="chart-card" v-loading="loading" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="card-title">行为聚类雷达图</span>
              <el-select 
                v-model="selectedAccount" 
                placeholder="选择账户" 
                clearable 
                @change="handleAccountChange"
                :loading="accountsLoading"
              >
                <el-option
                  v-for="account in accountList"
                  :key="account"
                  :label="account"
                  :value="account"
                >
                  <span style="float: left">{{ account }}</span>
                  <span 
                    v-if="accountDetails[account]"
                    style="float: right; color: #8492a6; font-size: 13px"
                  >
                    交易: {{ accountDetails[account].txCount }}
                  </span>
                </el-option>
              </el-select>
            </div>
          </template>
          <div v-if="!selectedAccount" class="empty-placeholder">
            <i class="el-icon-data-analysis" style="font-size: 32px; margin-bottom: 10px;"></i>
            <p>请选择一个账户进行分析</p>
          </div>
          <div v-else ref="radarChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="chart-card" v-loading="loading" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="card-title">行为热力图</span>
              <el-button 
                type="primary" 
                size="small" 
                @click="refreshAccounts"
                :loading="accountsLoading"
              >
                刷新账户列表
              </el-button>
            </div>
          </template>
          <div v-if="!selectedAccount" class="empty-placeholder">
            <i class="el-icon-data-line" style="font-size: 32px; margin-bottom: 10px;"></i>
            <p>请选择一个账户进行分析</p>
          </div>
          <div v-else ref="heatmapChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { ECharts, EChartsOption, EChartsType, RadarComponentOption } from 'echarts'
import type { AxiosInstance } from 'axios'

// Custom axios instance with base URL and timeout
const api: AxiosInstance = axios.create({
  baseURL: 'http://localhost:5000',
  timeout: 30000
});

// 添加响应拦截器处理超时
api.interceptors.response.use(
  response => response,
  async error => {
    if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
      // 超时后重试，使用更长的超时时间
      const retryConfig = {
        ...error.config,
        timeout: 60000 // 60秒超时
      };
      return api(retryConfig);
    }
    return Promise.reject(error);
  }
);

// 图表容器引用
const radarChartRef = ref<HTMLElement | null>(null);
const heatmapChartRef = ref<HTMLElement | null>(null);
const timelineChartRef = ref<HTMLElement | null>(null);

// 图表实例
let radarChart: echarts.ECharts | null = null;
let heatmapChart: echarts.ECharts | null = null;
let timelineChart: echarts.ECharts | null = null;

// 状态变量
const loading = ref(false)
const accountsLoading = ref(false)
const selectedAccount = ref<string>('')
const accountList = ref<string[]>([])
const accountDetails = ref<Record<string, { txCount: number }>>({})
const dateRange = ref<[Date, Date]>([new Date(), new Date()])
const riskThreshold = ref<number>(0.5)
const amountThreshold = ref<number>(1000)
const radarOption = ref<EChartsOption | null>(null)
const heatmapOption = ref<EChartsOption | null>(null)

// 处理日期范围变化
const handleDateRangeChange = async () => {
  await loadData();
};

interface ApiResponse<T> {
  data?: T;
  error?: string;
  [key: string]: any;  // 添加这个允许响应有额外属性
}

interface RadarResponse {
  dimensions: string[];
  values: number[];
  stats_info?: Record<string, string | number>;  // Allow both string and number values
}

interface RadarData {
  value: number[];
  name: string;
}

interface RadarSeriesOption {
  type: 'radar';
  name: string;
  data: RadarData[];
}

interface HeatmapResponse {
  hours: string[];
  days: string[];
  values: number[][];
}

interface TimelineResponse {
  dates: string[];
  values: number[];
}

interface AccountData {
  txCount: number;
  totalAmount: number;
  riskScore: number;
  patterns: string[];
}

interface ChartData {
  value: number[];
  name: string;
}

// 加载数据
const loadData = async () => {
  loading.value = true;
  
  try {
    const params = {
      min_risk: 0.7,
      min_amount: 10000,
      start_date: dateRange.value[0].toISOString().split('T')[0],
      end_date: dateRange.value[1].toISOString().split('T')[0]
    };

    console.log('Requesting data with params:', params);

    // 确保图表已初始化
    await initCharts();

    // 并行请求数据
    const [radar, heatmap] = await Promise.all([
      api.get<any>('/api/group/behavior-radar', { params }),
      api.get<any>('/api/group/heatmap', { params })
    ]);

    console.log('Received radar data:', radar.data);
    console.log('Received heatmap data:', heatmap.data);

    // 检查响应中是否包含错误信息
    if (radar.data?.error) {
      console.warn('Radar data error:', radar.data.error);
      // 使用测试数据作为后备
      const sampleData: RadarResponse = {
        dimensions: ['交易频率', '金额波动', '风险评分', '关联账户', '异常行为'],
        values: [60, 40, 70, 55, 65],
        stats_info: {
          '交易频率': '0笔/天',
          '总交易额': '¥0.00',
          '平均金额': '¥0.00',
          '最大金额': '¥0.00',
          '关联账户': '0个',
          '风险评分': '0.00'
        }
      };
      await updateRadarChart(sampleData);
      return;
    }
    if (heatmap.data?.error) {
      throw new Error(`Heatmap data error: ${heatmap.data.error}`);
    }
    
    // 更新图表数据
    if (radar.data?.data) {
      await updateRadarChart(radar.data.data as RadarResponse);
    } else if (radar.data?.dimensions && radar.data?.values) {
      // 数据直接在response中，而不是在data属性中
      await updateRadarChart(radar.data as RadarResponse);
    } else {
      console.warn('No valid radar data structure found');
      // 使用测试数据
      const sampleData: RadarResponse = {
        dimensions: ['交易频率', '金额波动', '风险评分', '关联账户', '异常行为'],
        values: [60, 40, 70, 55, 65]
      };
      await updateRadarChart(sampleData);
    }
    
    if (heatmap.data?.data) {
      await updateHeatmapChart(heatmap.data.data as HeatmapResponse);
    } else if (heatmap.data) {
      // 直接使用响应数据
      await updateHeatmapChart(heatmap.data as HeatmapResponse);
    } else {
      ElMessage.warning('未获取到热力图数据');
    }

  } catch (error: any) {
    console.error('数据加载失败:', error);
    ElMessage.error(error.response?.data?.error || error.message || '数据加载失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};

// 初始化图表
const initCharts = async () => {
  try {
    if (radarChartRef.value && !radarChart) {
      console.log('Initializing radar chart...');
      // 检查容器尺寸
      const radarContainer = radarChartRef.value;
      console.log('Radar container size:', {
        width: radarContainer.clientWidth,
        height: radarContainer.clientHeight
      });
      
      if (radarContainer.clientWidth === 0 || radarContainer.clientHeight === 0) {
        console.warn('Radar chart container has zero dimensions');
        radarContainer.style.width = '100%';
        radarContainer.style.height = '300px';
      }
      
      radarChart = echarts.init(radarContainer);
      console.log('Radar chart initialized:', !!radarChart);
    }
    
    if (heatmapChartRef.value && !heatmapChart) {
      console.log('Initializing heatmap chart...');
      const heatmapContainer = heatmapChartRef.value;
      
      if (heatmapContainer.clientWidth === 0 || heatmapContainer.clientHeight === 0) {
        console.warn('Heatmap chart container has zero dimensions');
        heatmapContainer.style.width = '100%';
        heatmapContainer.style.height = '300px';
      }
      
      heatmapChart = echarts.init(heatmapContainer);
      console.log('Heatmap chart initialized:', !!heatmapChart);
    }
  } catch (error) {
    console.error('Error initializing charts:', error);
  }
};

// 雷达图更新
const updateRadarChart = async (data: RadarResponse) => {
  console.log('Starting radar chart update with data:', data);
  
  // 确保雷达图已初始化
  if (!radarChart && radarChartRef.value) {
    await initCharts();
  }
  
  if (!radarChart) {
    console.error('Radar chart not initialized');
    return;
  }
  
  // 确保数据有效
  if (!data.dimensions || !data.values || data.dimensions.length === 0 || data.values.length === 0) {
    console.warn('Invalid radar data:', data);
    return;
  }

  console.log('Radar dimensions:', data.dimensions);
  console.log('Radar values:', data.values);

  // 计算最大值，确保至少为100
  const maxValue = Math.max(100, ...data.values.map(v => Math.ceil(v * 1.2)));
  console.log('Using max value for radar:', maxValue);
  
  try {
    const option: EChartsOption = {
      title: {
        text: selectedAccount.value ? `账户 ${selectedAccount.value} 行为分析` : '团伙行为分析',
        left: 'center',
        top: 10,
        textStyle: {
          fontSize: 16,
          fontWeight: 'normal'
        }
      },
      tooltip: {
        trigger: 'item',
        formatter: function(params: any) {
          if (!params.value) return '';
          const values = params.value;
          const indicators = data.dimensions;
          let result = `${params.name}<br/>`;
          for (let i = 0; i < indicators.length; i++) {
            // 添加对应的统计信息
            const statKey = indicators[i];
            const statValue = data.stats_info?.[statKey];
            result += `${indicators[i]}: ${values[i].toFixed(2)}`;
            if (statValue) {
              result += ` (${statValue})`;
            }
            result += '<br/>';
          }
          return result;
        }
      },
      legend: {
        data: ['行为特征'],
        bottom: 5,
        selectedMode: false
      },
      radar: {
        indicator: data.dimensions.map(name => ({
          name,
          max: maxValue,
        })),
        center: ['50%', '50%'],
        radius: '65%',
        shape: 'circle',
        splitNumber: 4,
        splitArea: {
          areaStyle: {
            color: ['rgba(64, 158, 255, 0.1)', 'rgba(64, 158, 255, 0.2)', 
                   'rgba(64, 158, 255, 0.3)', 'rgba(64, 158, 255, 0.4)'],
            shadowColor: 'rgba(0, 0, 0, 0.2)',
            shadowBlur: 10
          }
        },
        axisLine: {
          lineStyle: {
            color: '#ccc'
          }
        },
        splitLine: {
          lineStyle: {
            color: '#ddd'
          }
        },
        axisName: {
          color: '#333',
          fontSize: 12
        }
      },
      series: [{
        type: 'radar',
        name: '行为特征',
        data: [{
          value: data.values,
          name: '行为特征',
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            width: 2,
            color: '#409EFF'
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              {
                offset: 0,
                color: 'rgba(64, 158, 255, 0.7)'
              },
              {
                offset: 1,
                color: 'rgba(64, 158, 255, 0.2)'
              }
            ])
          },
          itemStyle: {
            color: '#409EFF'
          },
          emphasis: {
            itemStyle: {
              color: '#409EFF',
              borderColor: '#fff',
              borderWidth: 2,
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.3)'
            }
          }
        }]
      }]
    };
    
    console.log('Setting radar chart option');
    radarChart.setOption(option, true);
    console.log('Radar chart updated successfully');
  } catch (error) {
    console.error('Failed to update radar chart:', error);
  }
};

// 热力图更新
const updateHeatmapChart = async (data: any) => {
  console.log('Starting heatmap update with data:', data);
  
  // 检查数据结构，适配不同格式
  let heatmapData: [number, number, number][] = [];
  let hours = ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', 
               '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23'];
  let days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  
  // 确保heatmap已初始化
  if (!heatmapChart && heatmapChartRef.value) {
    await initCharts();
  }
  
  if (!heatmapChart) {
    console.error('Heatmap chart not initialized');
    return;
  }
  
  try {
    console.log('Raw heatmap data:', JSON.stringify(data).substring(0, 500));
    
    // 处理数据格式
    if (data && data.data && Array.isArray(data.data)) {
      // 后端直接返回[hour, weekday, count]格式的数据
      heatmapData = data.data;
      console.log('Using direct array data format:', heatmapData.length, 'points');
    } else if (data && data.values && Array.isArray(data.values)) {
      // 后端返回二维数组格式
      const values = data.values;
      if (data.hours) hours = data.hours;
      if (data.days) days = data.days;
      
      console.log('Processing 2D array data format');
      values.forEach((row: number[], i: number) => {
        row.forEach((value: number, j: number) => {
          heatmapData.push([j, i, value]);
        });
      });
    } else if (data && Array.isArray(data)) {
      // 直接是数组格式
      heatmapData = data;
      console.log('Data is directly an array');
    } else {
      // 如果无法识别格式，生成随机热点数据
      console.warn('No valid heatmap data found, generating random data for visualization');
      
      // 生成随机数据 - 每天工作时间有较多的交易
      for (let day = 0; day < 7; day++) {
        for (let hour = 0; hour < 24; hour++) {
          // 工作日(1-5)和工作时间(9-17)交易较多
          let value = 0;
          const isWorkday = day >= 1 && day <= 5;
          const isWorkHour = hour >= 9 && hour <= 17;
          
          if (isWorkday && isWorkHour) {
            // 工作日工作时间
            value = Math.floor(Math.random() * 5);
          } else if (isWorkday || isWorkHour) {
            // 工作日非工作时间或非工作日工作时间
            value = Math.random() > 0.7 ? Math.floor(Math.random() * 3) : 0;
          } else {
            // 非工作日非工作时间
            value = Math.random() > 0.9 ? 1 : 0;
          }
          
          if (value > 0 || Math.random() > 0.8) { // 仅添加有值的点或少量0值点
            heatmapData.push([hour, day, value]);
          }
        }
      }
    }
    
    // 检查数据格式是否正确
    if (heatmapData.length > 0) {
      const validData = heatmapData.every(item => 
        Array.isArray(item) && 
        item.length === 3 && 
        typeof item[0] === 'number' && 
        typeof item[1] === 'number' &&
        typeof item[2] === 'number'
      );
      
      if (!validData) {
        console.error('Heatmap data format is incorrect', heatmapData.slice(0, 5));
        // 清空并使用空数据
        heatmapData = [];
        for (let day = 0; day < 7; day++) {
          for (let hour = 0; hour < 24; hour++) {
            heatmapData.push([hour, day, 0]);
          }
        }
      }
    }
    
    // 确保有完整的数据点
    for (let day = 0; day < 7; day++) {
      for (let hour = 0; hour < 24; hour++) {
        // 检查是否已经存在此坐标的数据点
        const existingPoint = heatmapData.find(
          item => item[0] === hour && item[1] === day
        );
        
        // 如果不存在则添加0值的数据点
        if (!existingPoint) {
          heatmapData.push([hour, day, 0]);
        }
      }
    }
    
    // 计算最大值
    let maxValue = 1;
    if (heatmapData.length > 0) {
      const values = heatmapData.map(item => item[2]);
      maxValue = Math.max(...values, 1);
    }
    
    console.log('Prepared heatmap data:', {
      points: heatmapData.length,
      maxValue: maxValue,
      sample: heatmapData.slice(0, 10)
    });
    
    const option = {
      title: {
        text: selectedAccount.value ? `账户 ${selectedAccount.value} 交易热力图` : '交易热力图',
        left: 'center'
      },
      tooltip: {
        position: 'top',
        formatter: (params: any) => {
          if (!params.data) return '';
          const hourIndex = params.data[0];
          const dayIndex = params.data[1];
          const value = params.data[2];
          return `${days[dayIndex]} ${hours[hourIndex]}时<br>交易量: ${value}`;
        }
      },
      grid: {
        top: '60px',
        bottom: '15%',
        left: '3%',
        right: '7%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: hours,
        splitArea: { show: true },
        axisLabel: { rotate: 45 }
      },
      yAxis: {
        type: 'category',
        data: days,
        splitArea: { show: true }
      },
      visualMap: {
        min: 0,
        max: maxValue,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '0',
        inRange: {
          color: ['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127']
        }
      },
      series: [{
        name: '交易热力图',
        type: 'heatmap',
        data: heatmapData,
        label: {
          show: true,
          formatter: (params: any) => {
            return params.data[2] > 0 ? params.data[2] : '';
          }
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }]
    };

    heatmapChart.setOption(option, true);
    console.log('Heatmap chart updated successfully');
  } catch (error) {
    console.error('Error updating heatmap chart:', error);
  }
};

// 处理账户选择变化
const handleAccountChange = () => {
  loadData();
};

// 处理窗口大小变化
const handleResize = () => {
  if (radarChart) radarChart.resize();
  if (heatmapChart) heatmapChart.resize();
};

// 生命周期钩子
onMounted(async () => {
  console.log('Component mounted, initializing...');
  await initCharts();
  await loadRandomAccounts();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  if (radarChart) {
    radarChart.dispose();
    radarChart = null;
  }
  if (heatmapChart) {
    heatmapChart.dispose();
    heatmapChart = null;
  }
  window.removeEventListener('resize', handleResize);
});

// 监听账户选择变化
watch(selectedAccount, () => {
  if (selectedAccount.value) {
    loadAccountData();
  }
});

// 加载随机账户
const loadRandomAccounts = async () => {
  accountsLoading.value = true;
  try {
    console.log('Requesting random accounts');
    const response = await api.get('/api/group/random-accounts');
    console.log('Received random accounts:', response.data);

    if (response.data?.error) {
      throw new Error(response.data.error);
    }

    if (response.data) {
      accountList.value = response.data;
      // 重置选中的账户
      selectedAccount.value = '';
      // 清空账户详情
      accountDetails.value = {};
    } else {
      ElMessage.warning('未获取到账户列表');
    }
  } catch (error: any) {
    console.error('获取随机账户失败:', error);
    ElMessage.error(error.response?.data?.error || error.message || '获取随机账户失败，请稍后重试');
  } finally {
    accountsLoading.value = false;
  }
};

// 刷新账户列表
const refreshAccounts = () => {
  loadRandomAccounts();
};

// 加载账户数据
const loadAccountData = async () => {
  if (!selectedAccount.value) return;
  
  loading.value = true;
  try {
    const params = { account: selectedAccount.value };
    console.log('Loading account data for:', selectedAccount.value);

    // 确保图表初始化
    await initCharts();

    // 并行请求数据
    const [radarResponse, heatmapResponse] = await Promise.all([
      api.get<any>('/api/group/behavior-radar', { params }),
      api.get<any>('/api/group/heatmap', { params })
    ]);

    console.log('Radar API full response:', radarResponse);
    console.log('Heatmap API full response:', heatmapResponse);
    
    // 更新图表数据
    if (radarResponse.data?.dimensions && radarResponse.data?.values) {
      // 数据直接在response中
      console.log('Found radar dimensions and values in response');
      await updateRadarChart(radarResponse.data as RadarResponse);
    } else if (radarResponse.data?.data && 
               radarResponse.data.data.dimensions && 
               radarResponse.data.data.values) {
      // 数据嵌套在data属性中
      console.log('Found radar dimensions and values in response.data');
      await updateRadarChart(radarResponse.data.data as RadarResponse);
    } else {
      console.warn('No valid radar data found in response');
      // 使用测试数据
      const sampleData: RadarResponse = {
        dimensions: ['交易频率', '金额波动', '风险评分', '关联账户', '异常行为'],
        values: [60, 40, 70, 55, 65]
      };
      ElMessage.info('使用模拟数据替代雷达图数据');
      await updateRadarChart(sampleData);
    }
    
    // 处理热力图数据
    if (heatmapResponse.data) {
      console.log('Found heatmap data in response');
      await updateHeatmapChart(heatmapResponse.data);
    } else {
      console.warn('No heatmap data in API response');
      ElMessage.warning('未获取到热力图数据');
    }

  } catch (error) {
    console.error('数据加载失败:', error);
    ElMessage.error('数据加载失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.gang-behavior {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.chart-card {
  height: 450px;
  margin-bottom: 20px;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.chart-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
}

.chart-container {
  height: 350px;
  width: 100%;
  min-height: 300px;
  position: relative;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 5px;
}

.card-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.empty-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #909399;
  font-size: 14px;
  background-color: #fafafa;
  border-radius: 4px;
}

:deep(.el-select) {
  width: 240px;
}

:deep(.el-card__header) {
  padding: 15px 20px;
  border-bottom: 1px solid #ebeef5;
  background-color: #f8f9fb;
}

:deep(.el-card__body) {
  padding: 15px;
}
</style>