<template>
  <div class="chat-container">
    <el-card class="chat-card">
      <template #header>
        <div class="card-header">
          <span>AI智能对话</span>
          <el-button v-if="messages.length > 1" type="text" @click="handleFeedback(true)">
            <el-icon><Thumb /></el-icon>
          </el-button>
          <el-button v-if="messages.length > 1" type="text" @click="handleFeedback(false)">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </template>
      
      <div class="chat-content" ref="chatContentRef">
        <div v-for="(message, index) in messages" :key="index" :class="['message', message.type]">
          <el-avatar :size="32" :icon="message.type === 'user' ? 'UserFilled' : 'Service'" />
          <div class="message-content">
            <p>{{ message.content }}</p>
          </div>
        </div>
        <div v-if="loading" class="message ai">
          <el-avatar :size="32" icon="Service" />
          <div class="message-content">
            <p><el-skeleton :rows="3" animated /></p>
          </div>
        </div>
      </div>

      <div class="chat-input">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="3"
          placeholder="请输入您的问题..."
          @keyup.enter="handleSend"
        />
        <el-button type="primary" @click="handleSend" :loading="loading">
          发送
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import { useChatApi } from '@/api/chat'
import { debounce } from 'lodash-es'
// 使用Element Plus图标

// 使用聊天API
const { sendMessage, getHistory, submitFeedback } = useChatApi()

const chatContentRef = ref(null)
const inputMessage = ref('')
const loading = ref(false)
const messages = ref([])
const sessionId = ref('')

// 滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (chatContentRef.value) {
    chatContentRef.value.scrollTop = chatContentRef.value.scrollHeight
  }
}

// 获取历史记录
const getChatHistory = async () => {
  try {
    // 从服务器获取历史记录
    const response = await getHistory(sessionId.value)
    
    // 如果有会话 ID，保存它
    if (response.data && response.data.sessionId) {
      sessionId.value = response.data.sessionId
      localStorage.setItem('chatSessionId', sessionId.value)
    }
    
    // 显示欢迎消息，无论有没有历史记录
    messages.value = [{
      type: 'ai',
      content: '你好！我是智能反欺诈助手。我可以帮助你：\n\n1. 分析交易风险\n2. 识别可疑行为\n3. 提供风险防范建议\n4. 解答反欺诈相关问题\n\n请问有什么我可以帮你的吗？'
    }]
    
    await scrollToBottom()
  } catch (error) {
    console.error('获取历史记录失败:', error)
    // 发生错误时也显示欢迎消息
    messages.value = [{
      type: 'ai',
      content: '你好！我是智能反欺诈助手。我可以帮助你：\n\n1. 分析交易风险\n2. 识别可疑行为\n3. 提供风险防范建议\n4. 解答反欺诈相关问题\n\n请问有什么我可以帮你的吗？'
    }]
  }
}

// 提交反馈
const handleFeedback = async (isPositive) => {
  if (messages.value.length <= 1) return
  
  try {
    // 获取最后一条AI消息
    const lastAiMessage = [...messages.value].reverse().find(msg => msg.type === 'ai')
    if (!lastAiMessage) return
    
    await submitFeedback({
      sessionId: sessionId.value,
      messageId: lastAiMessage.id, // 如果后端API需要消息ID
      feedback: isPositive ? 'positive' : 'negative'
    })
    
    ElMessage.success(isPositive ? '感谢您的肯定！' : '感谢您的反馈，我们会继续改进')
  } catch (error) {
    console.error('提交反馈失败:', error)
    ElMessage.error('提交反馈失败，请稍后重试')
  }
}

const handleSend = debounce(async () => {
  try {
    const message = inputMessage.value.trim()
    if (!message) {
      return
    }

    // 清空输入并显示用户消息
    inputMessage.value = ''
    const userMessage = {
      type: 'user',
      content: message
    }
    messages.value.push(userMessage)
    await scrollToBottom()

    // 设置加载状态
    loading.value = true
    
    // 发送请求
    const payload = {
      content: message,
      sessionId: sessionId.value
    }
    
    const response = await sendMessage(payload)
    console.log('Chat Response:', response)
    
    // 处理不同的响应格式
    let content = '', messageId = null
    
    if (response.data) {
      if (typeof response.data === 'string') {
        // 纯文本响应
        content = response.data
      } else if (response.data.content) {
        // { content: string, ... } 格式
        content = response.data.content
        messageId = response.data.id || response.data.messageId
      } else if (response.data.message && response.data.message.content) {
        // { message: { content: string, ... }, ... } 格式
        content = response.data.message.content
        messageId = response.data.message.id || response.data.messageId
      } else {
        console.warn('未知响应格式，尝试解析:', response.data)
        content = '收到响应，但格式无法解析'
      }
      
      // 如果返回了sessionId，保存它
      if (response.data.sessionId) {
        sessionId.value = response.data.sessionId
        localStorage.setItem('chatSessionId', sessionId.value)
      }
    } else {
      throw new Error('服务器响应为空')
    }
    
    // 添加AI消息
    const aiMessage = {
      type: 'ai',
      content: content || '抱歉，我无法理解您的问题',
      id: messageId // 存储消息ID用于反馈
    }
    messages.value.push(aiMessage)
    
    await scrollToBottom()
  } catch (error) {
    console.error('发送消息失败:', error)
    
    // 更详细地处理错误类型
    let errorMessage = '抱歉，发生了错误，请稍后重试。'
    
    if (error.code === 'ERR_NETWORK') {
      errorMessage = '网络连接失败，请检查服务器是否在运行。'
    } else if (error.code === 'ECONNABORTED') {
      errorMessage = '请求超时，服务器响应时间过长。请稍后再试或提问简单一些的问题。'
    } else if (error.response) {
      // 服务器返回了错误状态码
      if (error.response.status === 404) {
        errorMessage = 'API未找到，请检查服务器配置和路由。'
      } else if (error.response.status === 403) {
        errorMessage = '没有权限执行此操作，请检查您的登录状态。'
      } else if (error.response.status >= 500) {
        errorMessage = '服务器内部错误，请联系管理员。'
      }
    }
    
    // 添加错误消息
    messages.value.push({
      type: 'ai',
      content: errorMessage
    })
    
    ElMessage.error({
      message: errorMessage,
      duration: 5000
    })
    
    await scrollToBottom()
  } finally {
    loading.value = false
  }
}, 300)

onMounted(async () => {
  try {
    // 尝试获取历史记录，如果失败则显示默认欢迎消息
    await getChatHistory()
    
    // 显示通知，告知用户聊天服务已连接
    ElNotification({
      title: '聊天服务已连接',
      message: '智能对话助手已准备就绪，可以开始对话',
      type: 'success',
      duration: 3000
    })
  } catch (error) {
    console.error('初始化聊天界面失败:', error)
    
    // 添加默认欢迎消息
    messages.value = [{
      type: 'ai',
      content: '你好！我是智能反欺诈助手。我可以帮助你：\n\n1. 分析交易风险\n2. 识别可疑行为\n3. 提供风险防范建议\n4. 解答反欺诈相关问题\n\n请问有什么我可以帮你的吗？'
    }]
    
    if (error.code === 'ERR_NETWORK') {
      ElNotification({
        title: '聊天服务连接失败',
        message: '无法连接到端口8080的聊天服务，请确保后端服务已启动',
        type: 'error',
        duration: 0
      })
    }
  }
})
</script>

<style lang="scss" scoped>
.chat-container {
  height: calc(100vh - 140px);
  padding: 20px;

  .chat-card {
    height: 100%;
    display: flex;
    flex-direction: column;

    :deep(.el-card__body) {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 0;
    }
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    
    .el-button {
      margin-left: auto;
      padding: 4px;
    }
  }

  .chat-content {
    height: calc(100% - 120px);
    overflow-y: auto;
    padding: 20px;
  }
  
  .chat-input {
    position: sticky;
    bottom: 0;
    background: white;
    padding: 20px;
    border-top: 1px solid #dcdfe6;
  }
  
  :deep(.el-card__body) {
    height: 100%;
    overflow: hidden;
  }

    .message {
      display: flex;
      align-items: flex-start;
      margin-bottom: 20px;

      &.ai {
        flex-direction: row;

        .message-content {
          margin-left: 10px;
          background-color: #f4f4f5;
        }
      }

      &.user {
        flex-direction: row-reverse;

        .message-content {
          margin-right: 10px;
          background-color: #e6f6ff;
        }
      }

      .message-content {
        max-width: 80%;
        padding: 10px 15px;
        border-radius: 8px;

        p {
          margin: 0;
          white-space: pre-wrap;
          word-break: break-word;
        }
      }
    }

    .chat-input {
      padding: 20px;
      border-top: 1px solid #dcdfe6;

      .el-button {
        width: 100%;
        margin-top: 10px;
      }
    }
  }
</style>