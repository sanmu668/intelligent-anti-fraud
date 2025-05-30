import axios from 'axios'

// 创建API实例
const api = axios.create({
  baseURL: 'http://localhost:8080', // 直接指向Java服务器的端口
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

// 添加请求拦截器
api.interceptors.request.use(
  config => {
    console.log('请求配置:', config.method, config.url, config.data);
    return config;
  },
  error => {
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

// 添加响应拦截器
api.interceptors.response.use(
  response => {
    console.log('响应数据:', response.status, response.data);
    return response;
  },
  error => {
    console.error('API错误:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      message: error.message,
      code: error.code
    })
    return Promise.reject(error)
  }
)

// 直接使用Java后端的路径
const CHAT_API_PATH = '/chat'

export function useChatApi() {
  /**
   * 发送消息
   * @param {Object} payload - 消息对象，包含content和sessionId
   * @returns {Promise} API响应
   */
  const sendMessage = async (payload) => {
    try {
      // 确保有sessionId
      if (!payload.sessionId) {
        payload.sessionId = localStorage.getItem('chatSessionId') || Date.now().toString();
        // 保存到本地存储以便后续使用
        localStorage.setItem('chatSessionId', payload.sessionId);
      }

      // 格式化请求数据，确保字段名称正确
      // 根据Java ChatController中的ChatRequestDTO调整参数名
      const requestData = {
        message: payload.content,  // 改回message以匹配Java DTO
        sessionId: payload.sessionId
      };

      console.log('Sending message:', requestData);

      // 直接请求Java后端
      const response = await api.post(`${CHAT_API_PATH}/message`, requestData);

      console.log('Message response:', response);

      return response;
    } catch (error) {
      console.error('发送消息失败:', error);
      throw error;
    }
  }

  /**
   * 获取历史记录
   * @param {string} sessionId - 会话ID
   * @returns {Promise} API响应
   */
  const getHistory = async (sessionId) => {
    try {
      // 初始化时不请求历史记录，直接返回一个带欢迎消息的模拟响应
      return {
        data: {
          sessionId: sessionId || Date.now().toString(),
          messages: []
        }
      };
    } catch (error) {
      console.error('获取历史记录失败:', error);
      throw error;
    }
  }

  /**
   * 提交反馈
   * @param {Object} payload - 反馈对象，包含sessionId, messageId和feedback
   * @returns {Promise} API响应
   */
  const submitFeedback = async (payload) => {
    try {
      // 目前Java后端还没有实现反馈功能，返回一个模拟成功的响应
      return {
        data: { success: true, message: "反馈已提交" },
        status: 200
      };
    } catch (error) {
      console.error('提交反馈失败:', error);
      throw error;
    }
  }

  return { sendMessage, getHistory, submitFeedback }
}

export default useChatApi 