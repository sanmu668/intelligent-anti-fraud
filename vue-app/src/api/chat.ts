import request from './request'
import { API_ENDPOINTS } from './config'

// 聊天API基础URL
const CHAT_API_BASE_URL = 'http://localhost:8080'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: number
}

export interface ChatResponse {
  message: ChatMessage
  error?: string
}

export const sendMessage = async (message: string): Promise<ChatResponse> => {
  try {
    const response = await request({
      url: `${CHAT_API_BASE_URL}${API_ENDPOINTS.CHAT.SEND}`,
      method: 'post',
      data: { message }
    })

    // SpringBoot 响应格式处理
    if (!response.data || !response.data.data) {
      throw new Error('服务器响应格式错误')
    }

    return {
      message: {
        role: 'assistant',
        content: response.data.data,
        timestamp: Date.now()
      }
    }
  } catch (error: any) {
    console.error('Chat API error:', error)
    return {
      message: {
        role: 'assistant',
        content: '抱歉，服务器出现错误，请稍后重试。',
        timestamp: Date.now()
      },
      error: error.message
    }
  }
}

export const getChatHistory = async (): Promise<ChatMessage[]> => {
  try {
    const response = await request({
      url: `${CHAT_API_BASE_URL}${API_ENDPOINTS.CHAT.HISTORY}`,
      method: 'get'
    })

    // SpringBoot 响应格式处理
    if (!response.data || !Array.isArray(response.data.data)) {
      return []
    }

    return response.data.data.map((item: any) => ({
      role: item.role || 'assistant',
      content: item.content,
      timestamp: item.timestamp
    }))
  } catch (error) {
    console.error('获取聊天历史失败:', error)
    return []
  }
}