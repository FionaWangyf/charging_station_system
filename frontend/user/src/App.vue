<template>
  <div class="app">
    <!-- WebSocket 连接状态指示器 -->
    <div v-if="showConnectionStatus" class="connection-status" :class="connectionStatusClass">
      <span class="status-indicator"></span>
      <span class="status-text">{{ connectionStatusText }}</span>
    </div>

    <!-- 登录页面 -->
    <LoginForm
      v-if="currentPage === 'login'"
      @switch-to-register="switchToRegister"
      @login-success="handleLoginSuccess"
    />

    <!-- 注册页面 -->
    <RegisterForm
      v-if="currentPage === 'register'"
      @switch-to-login="switchToLogin"
    />

    <!-- 主界面 -->
    <MainPage
      v-if="currentPage === 'main'"
      @switch-to-charging-details="switchToChargingDetails"
      @logout="handleLogout"
      :queue-info="queueInfo"
      :charging-session="chargingSession"
    />

    <!-- 充电详单页面 -->
    <ChargingDetailsPage
      v-if="currentPage === 'chargingDetails'"
      @switch-to-main="switchToMain"
    />

    <!-- 通知弹窗 -->
    <NotificationPopup
      v-if="showNotification"
      :notification="currentNotification"
      @close="dismissNotification"
    />
  </div>
</template>


<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import LoginForm from './components/LoginPage.vue'
import RegisterForm from './components/RegisterPage.vue'
import MainPage from './components/MainPage.vue'
import ChargingDetailsPage from './components/ChargingDetailsPage.vue'
import NotificationPopup from './components/NotificationPopup.vue'
import { useWebSocket } from './composables/useWebSocket'
import type { SystemNotification } from './types/websocket'

// 生成唯一的标签页 ID
const tabId = ref(`tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)

// 当前页面状态
const currentPage = ref<'login' | 'register' | 'main' | 'chargingDetails'>('login')

// 当前用户信息
const currentUser = ref<{ id: string; username: string } | null>(null)

// WebSocket 相关
const {
  status: wsStatus,
  isConnected,
  isConnecting,
  queueInfo,
  chargingSession,
  notifications,
  unreadNotificationCount,
  connect: connectWebSocket,
  disconnect: disconnectWebSocket,
  joinUserRoom,
  markNotificationAsRead,
  resetQueueInfo,
  resetChargingSession
} = useWebSocket()

// 通知相关
const showNotification = ref(false)
const currentNotification = ref<SystemNotification | null>(null)
const notificationQueue = ref<SystemNotification[]>([])

// 连接状态显示
const showConnectionStatus = ref(true)
const connectionStatusClass = computed(() => {
  switch (wsStatus.value) {
    case 'connected':
      return 'status-connected'
    case 'connecting':
      return 'status-connecting'
    case 'disconnected':
      return 'status-disconnected'
    case 'error':
      return 'status-error'
    default:
      return 'status-disconnected'
  }
})

const connectionStatusText = computed(() => {
  switch (wsStatus.value) {
    case 'connected':
      return '已连接'
    case 'connecting':
      return '连接中...'
    case 'disconnected':
      return '未连接'
    case 'error':
      return '连接错误'
    default:
      return '未连接'
  }
})

// 多标签页支持的 localStorage 操作
const getUserInfoKey = () => `userInfo_${tabId.value}`

const saveUserInfo = (userInfo: any) => {
  localStorage.setItem(getUserInfoKey(), JSON.stringify(userInfo))
  console.log(`💾 保存用户信息到标签页 ${tabId.value}:`, userInfo)
}

const getSavedUserInfo = () => {
  return localStorage.getItem(getUserInfoKey())
}

const clearUserInfo = () => {
  localStorage.removeItem(getUserInfoKey())
  console.log(`🗑️ 清除标签页 ${tabId.value} 的用户信息`)
}

// 切换到注册页面
const switchToRegister = () => {
  currentPage.value = 'register'
}

// 切换到登录页面
const switchToLogin = () => {
  currentPage.value = 'login'
  
  // 登出时断开 WebSocket 连接并重置状态
  if (currentUser.value) {
    disconnectWebSocket()
    currentUser.value = null
    resetQueueInfo()
    resetChargingSession()
  }
}

// 处理退出登录
const handleLogout = () => {
  console.log(`🚪 用户退出登录 (标签页: ${tabId.value})`)
  
  // 清除当前标签页的用户信息
  clearUserInfo()
  
  // 清除用户信息
  currentUser.value = null
  
  // 断开 WebSocket 连接
  disconnectWebSocket()
  
  // 重置状态
  resetQueueInfo()
  resetChargingSession()
  
  // 切换到登录页面
  switchToLogin()
}

// 验证用户登录状态
const validateUserSession = async (userInfo: any): Promise<boolean> => {
  try {
    const response = await fetch('/api/user/profile', {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json'
      }
    })
    
    if (response.ok) {
      const result = await response.json()
      if (result.success === true) {
        console.log(`✅ 用户会话验证成功 (标签页: ${tabId.value})`)
        return true
      }
    }
    
    console.warn(`⚠️ 用户会话已失效 (标签页: ${tabId.value})`)
    return false
  } catch (error) {
    console.error(`❌ 验证用户会话失败 (标签页: ${tabId.value}):`, error)
    return false
  }
}

// 处理登录成功
const handleLoginSuccess = async (userInfo: any) => {
  console.log(`🎉 登录成功 (标签页: ${tabId.value})，用户信息:`, userInfo)
  
  // 检查用户信息是否完整
  if (!userInfo) {
    console.error('❌ 用户信息为空')
    alert('登录数据为空，请重试')
    return
  }
  
  if (!userInfo.user_id && !userInfo.id) {
    console.error('❌ 登录响应数据不完整:', userInfo)
    alert('登录数据不完整，请重试')
    return
  }
  
  // 验证用户会话（用于自动登录时的验证）
  const isValidSession = await validateUserSession(userInfo)
  if (!isValidSession) {
    console.warn('⚠️ 用户会话无效，清除本地数据')
    clearUserInfo()
    switchToLogin()
    return
  }
  
  // 保存用户信息到当前标签页
  saveUserInfo(userInfo)
  
  // 保存用户信息
  currentUser.value = {
    id: userInfo.user_id || userInfo.id,
    username: userInfo.username
  }
  
  // 切换到主界面
  switchToMain()
  
  // 连接 WebSocket 并加入用户房间
  if (currentUser.value.id) {
    // 为每个标签页创建独立的连接
    connectWebSocket(currentUser.value.id)
    
    // 延迟加入用户房间，确保连接已建立
    setTimeout(() => {
      if (isConnected.value && currentUser.value) {
        joinUserRoom(currentUser.value.id)
      }
    }, 1000)
  }
}

// 切换到主界面
const switchToMain = () => {
  currentPage.value = 'main'
  console.log(`跳转到主界面 (标签页: ${tabId.value})`)
}

// 切换到充电详单页面
const switchToChargingDetails = () => {
  currentPage.value = 'chargingDetails'
  console.log(`跳转到充电详单页面 (标签页: ${tabId.value})`)
}

// 显示通知
const showNotificationPopup = (notification: SystemNotification) => {
  if (showNotification.value) {
    // 如果当前有通知在显示，加入队列
    notificationQueue.value.push(notification)
  } else {
    // 直接显示通知
    currentNotification.value = notification
    showNotification.value = true
  }
}

// 关闭通知
const dismissNotification = () => {
  showNotification.value = false
  
  // 标记当前通知为已读
  if (currentNotification.value) {
    markNotificationAsRead(currentNotification.value.id)
  }
  
  currentNotification.value = null
  
  // 显示队列中的下一个通知
  setTimeout(() => {
    if (notificationQueue.value.length > 0) {
      const nextNotification = notificationQueue.value.shift()
      if (nextNotification) {
        showNotificationPopup(nextNotification)
      }
    }
  }, 300)
}

// 自动隐藏连接状态指示器
const hideConnectionStatusAfterDelay = () => {
  setTimeout(() => {
    if (isConnected.value) {
      showConnectionStatus.value = false
    }
  }, 3000)
}

// 监听通知变化
watch(notifications, (newNotifications) => {
  const latestNotification = newNotifications[0]
  if (latestNotification && !latestNotification.read) {
    // 只显示重要通知（错误和警告）
    if (latestNotification.type === 'error' || latestNotification.type === 'warning') {
      showNotificationPopup(latestNotification)
    }
  }
}, { deep: true })

// 监听连接状态变化
watch(wsStatus, (newStatus) => {
  console.log(`📡 WebSocket 状态变化 (标签页: ${tabId.value}):`, newStatus)
  
  if (newStatus === 'connected') {
    showConnectionStatus.value = true
    hideConnectionStatusAfterDelay()
    
    // 连接成功后，如果用户已登录，加入用户房间
    if (currentUser.value) {
      setTimeout(() => {
        joinUserRoom(currentUser.value!.id)
      }, 500)
    }
  } else if (newStatus === 'error' || newStatus === 'disconnected') {
    showConnectionStatus.value = true
  }
})

// 页面可见性监听（处理页面切换时的连接状态）
const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible' && currentUser.value) {
    // 页面变为可见时，检查连接状态
    if (!isConnected.value) {
      console.log(`🔄 页面重新可见，尝试重连 WebSocket (标签页: ${tabId.value})`)
      connectWebSocket(currentUser.value.id)
    }
  }
}

// 生命周期钩子
onMounted(async () => {
  console.log(`🚀 应用启动 - 标签页ID: ${tabId.value}`)
  
  // 检查当前标签页是否有保存的用户信息
  const savedUserInfo = getSavedUserInfo()
  if (savedUserInfo) {
    try {
      const userInfo = JSON.parse(savedUserInfo)
      if (userInfo.user_id || userInfo.id) {
        console.log(`📱 检测到保存的用户信息，验证会话有效性... (标签页: ${tabId.value})`)
        
        // 验证会话有效性
        const isValid = await validateUserSession(userInfo)
        if (isValid) {
          console.log(`✅ 自动登录成功 (标签页: ${tabId.value})`)
          handleLoginSuccess(userInfo)
        } else {
          console.log(`❌ 会话已失效，清除本地数据 (标签页: ${tabId.value})`)
          clearUserInfo()
        }
      }
    } catch (error) {
      console.error(`❌ 解析保存的用户信息失败 (标签页: ${tabId.value}):`, error)
      clearUserInfo()
    }
  }
  
  // 监听页面可见性变化
  document.addEventListener('visibilitychange', handleVisibilityChange)
  
  // 监听页面关闭/刷新事件
  window.addEventListener('beforeunload', () => {
    if (currentUser.value) {
      console.log(`🔌 页面关闭，断开连接 (标签页: ${tabId.value})`)
      disconnectWebSocket()
    }
  })
})

onUnmounted(() => {
  console.log(`🔥 应用卸载 (标签页: ${tabId.value})`)
  
  // 断开 WebSocket 连接
  disconnectWebSocket()
  
  // 移除事件监听器
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>


<style scoped>
.app {
  width: 100%;
  height: 100vh;
  position: relative;
}

/* 连接状态指示器 */
.connection-status {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-connected {
  background: rgba(76, 175, 80, 0.9);
  color: white;
  border: 1px solid rgba(76, 175, 80, 0.3);
}

.status-connected .status-indicator {
  background: #fff;
  animation: pulse-green 2s infinite;
}

.status-connecting {
  background: rgba(255, 193, 7, 0.9);
  color: white;
  border: 1px solid rgba(255, 193, 7, 0.3);
}

.status-connecting .status-indicator {
  background: #fff;
  animation: pulse-yellow 1s infinite;
}

.status-disconnected {
  background: rgba(158, 158, 158, 0.9);
  color: white;
  border: 1px solid rgba(158, 158, 158, 0.3);
}

.status-disconnected .status-indicator {
  background: #fff;
}

.status-error {
  background: rgba(244, 67, 54, 0.9);
  color: white;
  border: 1px solid rgba(244, 67, 54, 0.3);
}

.status-error .status-indicator {
  background: #fff;
  animation: pulse-red 0.8s infinite;
}

/* 动画效果 */
@keyframes pulse-green {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.2);
  }
}

@keyframes pulse-yellow {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.3);
  }
}

@keyframes pulse-red {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.4);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .connection-status {
    top: 10px;
    right: 10px;
    font-size: 12px;
    padding: 6px 12px;
  }
  
  .status-indicator {
    width: 6px;
    height: 6px;
  }
}
</style>