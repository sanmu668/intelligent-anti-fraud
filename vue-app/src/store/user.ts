import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const token = ref('')
  const userInfo = ref({
    username: '',
    role: '',
    permissions: []
  })

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  function getToken(): string {
    return token.value || localStorage.getItem('token') || ''
  }

  function setUserInfo(info: any) {
    userInfo.value = info
  }

  function clearUserInfo() {
    token.value = ''
    userInfo.value = {
      username: '',
      role: '',
      permissions: []
    }
    localStorage.removeItem('token')
  }

  return {
    token,
    userInfo,
    setToken,
    getToken,
    setUserInfo,
    clearUserInfo
  }
})