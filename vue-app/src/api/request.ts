import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const request = axios.create({
  baseURL: 'http://localhost:5000',
  timeout: 60000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    // 这里可以添加认证信息等
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    return response
  },
  error => {
    console.error('Response error:', error)
    if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
      // 处理请求超时
      ElMessage.error('请求超时，服务器处理数据可能需要较长时间，请稍后再试')
    } else if (error.response) {
      // 服务器返回错误状态码
      ElMessage.error(error.response.data?.message || error.response.data?.error || '请求失败')
    } else if (error.request) {
      // 请求发出但没有收到响应
      ElMessage.error('无法连接到服务器，请检查API服务是否已启动')
    } else {
      // 请求配置出错
      ElMessage.error('请求配置错误')
    }
    return Promise.reject(error)
  }
)

export default request 