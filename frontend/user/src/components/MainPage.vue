<template>
  <div class="main-container">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <div class="logo-section">
        <div class="logo">
          <div class="logo-icon">🔌</div>
          <span class="logo-text">智能充电桩</span>
        </div>
      </div>

      <nav class="nav-menu">
        <div class="nav-item active">
          <span class="nav-icon">🏠</span>
          <span class="nav-text">主页</span>
        </div>
        <div class="nav-item" @click="emit('switchToChargingDetails')">
          <span class="nav-icon">⚡</span>
          <span class="nav-text">充电详单</span>
        </div>
      </nav>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content">
      <!-- 顶部用户信息区域 -->
      <div class="user-section">
        <div class="user-info">
          <div class="user-avatar">
            <div class="avatar-icon">👤</div>
          </div>
          <div class="user-details">
            <h2 class="user-title">账号</h2>
            <div class="user-data">
              <div class="info-row">
                <span class="info-label">账号：</span>
                <span class="info-value">{{ userInfo.username || 'xxxx' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">状态：</span>
                <span class="info-value" :class="{ 'online': isConnected }">
                  {{ isConnected ? '在线' : '离线' }}
                </span>
              </div>
            </div>
            <button class="reset-password-btn" @click="resetPassword">
              重置密码
            </button>
          </div>
        </div>

        <div class="action-buttons">
          <button class="action-btn primary" @click="viewChargingDetails">
            查看充电详单
          </button>
          <button class="action-btn secondary" @click="modifyChargingRequest">
            提交充电请求
          </button>
          <button class="action-btn logout" @click="logout">
            退出登录
          </button>
        </div>
      </div>

      <!-- 充电排队信息 -->
      <div class="queue-section">
        <div class="queue-info">
          <h3 class="queue-title">本车排队号码：</h3>
          <div class="queue-number">{{ displayQueueInfo.isStopped ? '--' : displayQueueInfo.currentNumber }}</div>
        </div>

        <div class="waiting-info">
          <span class="waiting-text">您前方还有</span>
          <span class="waiting-number">{{ displayQueueInfo.isStopped ? '--' : displayQueueInfo.waitingCount }}</span>
          <span class="waiting-text">辆</span>
        </div>

        <div v-if="!displayQueueInfo.isStopped" class="status-info">
          <div class="status-text" :class="{ 'charging': displayQueueInfo.waitingCount === 0 }">
            {{ displayQueueInfo.waitingCount === 0 ? '正在充电...' : displayQueueInfo.status }}
          </div>
          
          <!-- 显示预估等待时间 -->
          <div v-if="displayQueueInfo.estimatedWaitTime && displayQueueInfo.waitingCount > 0" class="estimated-time">
            预估等待时间：{{ Math.ceil(displayQueueInfo.estimatedWaitTime / 60) }} 分钟
          </div>
          
          <div v-if="displayQueueInfo.waitingCount === 0" class="charging-controls">
            <button class="stop-charging-btn" @click="stopCharging">
              停止充电
            </button>
            
            <!-- 显示充电信息 -->
            <div v-if="displayChargingSession" class="charging-info">
              <div class="charging-detail">
                <span>充电桩：{{ displayChargingSession.pileId }}</span>
              </div>
              <div class="charging-detail">
                <span>已充电量：{{ displayChargingSession.powerConsumed.toFixed(1) }} kWh</span>
              </div>
              <div class="charging-detail">
                <span>充电时长：{{ Math.floor(displayChargingSession.chargingDuration / 60) }} 分钟</span>
              </div>
            </div>
          </div>
          
          <div v-else class="loading-dots">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        </div>

        <!-- WebSocket 连接状态提示 -->
        <div v-if="!isConnected" class="connection-warning">
          <span class="warning-icon">⚠️</span>
          <span class="warning-text">实时更新已断开，排队信息可能不是最新的</span>
        </div>
      </div>
      
      <!-- 系统状态信息 -->
      <div v-if="isConnected" class="system-status">
        <h4>系统状态</h4>
        <div class="status-grid">
          <div class="status-item">
            <span class="status-label">排队中</span>
            <span class="status-value">{{ systemStatus.totalQueuing }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">充电中</span>
            <span class="status-value">{{ systemStatus.totalCharging }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">可用充电桩</span>
            <span class="status-value">{{ systemStatus.availablePiles }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 修改充电请求弹窗 -->
    <div v-if="showChargingModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">提交/修改充电请求</h3>
          <button class="close-btn" @click="closeModal">×</button>
        </div>

        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">充电模式</label>
            <select v-model="chargingRequest.mode" class="form-select">
              <option value="">请选择充电模式</option>
              <option value="fast">快充</option>
              <option value="trickle">慢充</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">充电量</label>
            <input
              v-model="chargingRequest.amount"
              type="number"
              placeholder="请输入充电量"
              class="form-input-modal"
              min="1"
              max="100"
            />
          </div>
        </div>

        <div class="modal-footer">
          <button class="submit-btn" @click="submitChargingRequest" :disabled="!isFormValid">
            提交
          </button>
        </div>
      </div>
    </div>

    <!-- 重置密码弹窗 -->
    <div v-if="showPasswordModal" class="modal-overlay" @click="closePasswordModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">重置密码</h3>
          <button class="close-btn" @click="closePasswordModal">×</button>
        </div>

        <div class="modal-body">
          <div class="form-group">
            <input
              v-model="passwordForm.oldPassword"
              type="password"
              placeholder="请输入原密码"
              class="form-input-modal password-input"
            />
          </div>

          <div class="form-group">
            <input
              v-model="passwordForm.newPassword"
              type="password"
              placeholder="请输入新密码"
              class="form-input-modal password-input"
            />
          </div>
        </div>

        <div class="modal-footer">
          <button class="submit-btn" @click="submitPasswordReset" :disabled="!isPasswordFormValid">
            提交
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import type { QueueInfo, ChargingSession } from '@/types/websocket'

// 定义 Props（从 App.vue 传入的 WebSocket 数据）
interface Props {
  queueInfo?: QueueInfo
  chargingSession?: ChargingSession | null
}

const props = withDefaults(defineProps<Props>(), {
  queueInfo: () => ({
    currentNumber: '--',
    waitingCount: 0,
    status: '未排队',
    isStopped: true
  }),
  chargingSession: null
})

// 定义事件
const emit = defineEmits<{
  switchToChargingDetails: []
  logout: []
}>()

// 使用 WebSocket 组合式 API
const {
  isConnected,
  requestSystemStatus,
  systemStatus,
  disconnect
} = useWebSocket()

// 原有的本地状态（保持兼容性）
const userInfo = ref({
  username: '',
  password: '',
})

// 使用传入的排队信息，如果没有传入则使用本地状态
const displayQueueInfo = computed(() => {
  return props.queueInfo
})

// 使用传入的充电会话信息
const displayChargingSession = computed(() => {
  return props.chargingSession
})

// 弹窗状态
const showChargingModal = ref(false)
const showPasswordModal = ref(false)

// 充电请求表单数据
const chargingRequest = ref({
  mode: '',
  amount: ''
})

// 重置密码表单数据
const passwordForm = ref({
  oldPassword: '',
  newPassword: ''
})

// 表单验证
const isFormValid = computed(() => {
  return chargingRequest.value.mode && chargingRequest.value.amount &&
         Number(chargingRequest.value.amount) > 0
})

// 重置密码表单验证
const isPasswordFormValid = computed(() => {
  return passwordForm.value.oldPassword && passwordForm.value.newPassword
})

// 监听 WebSocket 连接状态
watch(isConnected, (connected) => {
  if (connected) {
    console.log('✅ WebSocket 已连接，请求系统状态更新')
    requestSystemStatus()
  }
})

// 组件挂载时获取用户信息
onMounted(() => {
  // 从localStorage获取用户信息
  const storedUserInfo = localStorage.getItem('userInfo')
  if (storedUserInfo) {
    try {
      const parsed = JSON.parse(storedUserInfo)
      userInfo.value.username = parsed.username || parsed.account || '用户'
    } catch (error) {
      console.error('解析用户信息失败:', error)
    }
  }

  // 如果 WebSocket 已连接，请求系统状态
  if (isConnected.value) {
    requestSystemStatus()
  }
})

// 重置密码
const resetPassword = () => {
  showPasswordModal.value = true
}

// 查看充电详单
const viewChargingDetails = () => {
  emit('switchToChargingDetails')
}

// 修改充电请求
const modifyChargingRequest = () => {
  showChargingModal.value = true
}

// 退出登录
const logout = () => {
  if (confirm('确定要退出登录吗？')) {
    // 清除本地存储
    localStorage.removeItem('userInfo')
    
    // 断开 WebSocket 连接
    disconnect()
    
    // 触发退出登录事件
    emit('logout')
  }
}

// 关闭充电请求弹窗
const closeModal = () => {
  showChargingModal.value = false
  // 重置表单
  chargingRequest.value = {
    mode: '',
    amount: ''
  }
}

// 关闭重置密码弹窗
const closePasswordModal = () => {
  showPasswordModal.value = false
  // 重置表单
  passwordForm.value = {
    oldPassword: '',
    newPassword: ''
  }
}

// 提交充电请求（更新后的版本）
// 提交充电请求（健壮错误处理版本）
const submitChargingRequest = async () => {
  if (!isFormValid.value) {
    alert('请完整填写充电信息')
    return
  }

  const requestData = {
    charging_mode: chargingRequest.value.mode,
    requested_amount: Number(chargingRequest.value.amount)
  }

  console.log('📤 准备发送充电请求:', requestData)

  try {
    const response = await fetch('/api/charging/request', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(requestData)
    })

    console.log('📥 收到响应:', {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok,
      headers: Object.fromEntries(response.headers.entries())
    })

    // 获取响应文本
    let responseText = ''
    try {
      responseText = await response.text()
      console.log('📄 响应原始内容:', responseText)
    } catch (textError) {
      console.error('❌ 读取响应内容失败:', textError)
      alert('无法读取服务器响应，请稍后重试')
      return
    }

    // 检查是否有响应内容
    if (!responseText || responseText.trim() === '') {
      console.error('❌ 服务器返回空响应')
      alert(`服务器错误 (${response.status}): 服务器返回空响应，请检查后端日志`)
      return
    }

    // 尝试解析JSON
    let result
    try {
      result = JSON.parse(responseText)
      console.log('✅ JSON解析成功:', result)
    } catch (parseError) {
      console.error('❌ JSON解析失败:', parseError)
      console.log('📄 无法解析的内容:', responseText.substring(0, 200))
      
      // 如果是HTML错误页面
      if (responseText.includes('<html>') || responseText.includes('<!DOCTYPE')) {
        alert('服务器返回了HTML错误页面，可能是内部错误。请检查后端日志。')
      } else {
        alert(`服务器响应格式错误:\n${responseText.substring(0, 100)}...`)
      }
      return
    }

    // 处理HTTP状态码
    if (!response.ok) {
      console.error('❌ HTTP错误状态:', response.status)
      const errorMessage = result?.message || result?.error || `服务器错误 (${response.status})`
      alert(`提交失败: ${errorMessage}`)
      return
    }

    // 检查业务逻辑成功
    if (response.status === 201 && result.success === true) {
      console.log('🎉 充电请求提交成功')
      alert(`充电请求已提交！\n充电模式：${chargingRequest.value.mode === 'fast' ? '快充' : '慢充'}\n充电量：${chargingRequest.value.amount}kWh`)
      closeModal()
      
      // 请求更新系统状态
      if (isConnected.value) {
        requestSystemStatus()
      }
      
      // 延迟获取状态更新
      setTimeout(() => {
        if (typeof fetchSystemStatusViaHTTP === 'function') {
          fetchSystemStatusViaHTTP()
        }
        if (typeof fetchUserStatusViaHTTP === 'function') {
          fetchUserStatusViaHTTP()
        }
      }, 1000)
      
    } else {
      console.warn('⚠️ 业务逻辑失败:', result)
      const errorMsg = result?.message || result?.msg || '提交失败，请稍后重试'
      alert(`提交失败: ${errorMsg}`)
    }

  } catch (error) {
    console.error('💥 提交充电请求异常:', error)
    
    // 详细的错误分类
    if (error instanceof TypeError) {
      if (error.message.includes('fetch')) {
        alert('网络连接失败，请检查网络连接')
      } else if (error.message.includes('json')) {
        alert('服务器响应格式错误')
      } else {
        alert(`网络错误: ${error.message}`)
      }
    } else if (error instanceof SyntaxError) {
      alert('服务器响应解析错误，请联系管理员')
    } else {
      alert(`未知错误: ${error.message || '请稍后重试'}`)
    }
  }
}

// 提交重置密码
const submitPasswordReset = async () => {
  if (!isPasswordFormValid.value) {
    alert('请填写完整的密码信息')
    return
  }

  try {
    const response = await fetch('/api/user/change-password', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        old_password: passwordForm.value.oldPassword,
        new_password: passwordForm.value.newPassword,
        confirm_password: passwordForm.value.newPassword
      })
    })

    const result = await response.json()

    if (response.ok && result.success === true) {
      alert('密码重置成功！')
      closePasswordModal()
    } else {
      const errorMsg = result.message || '原密码错误或重置失败'
      alert(errorMsg)
    }
  } catch (error) {
    console.error('重置密码失败:', error)
    alert('网络错误，请稍后重试')
  }
}

// 停止充电（更新后的版本）
const stopCharging = async () => {
  if (!confirm('确定要停止充电吗？')) {
    return
  }

  try {
    const response = await fetch('/api/charging/stop', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include'
    })

    const result = await response.json()

    if (response.ok && result.success === true) {
      alert('充电已停止')
      
      // 请求更新系统状态
      if (isConnected.value) {
        requestSystemStatus()
      }
    } else {
      alert(result.message || '停止充电失败，请稍后重试')
    }
  } catch (error) {
    console.error('停止充电失败:', error)
    alert('网络错误，请稍后重试')
  }
}
</script>

<style scoped>
.main-container {
  display: flex;
  width: 100%;
  height: 100vh;
  background-color: #f5f5f5;
}

/* 侧边栏样式 */
.sidebar {
  width: 250px;
  background-color: #2c3e50;
  color: white;
  display: flex;
  flex-direction: column;
}

.logo-section {
  padding: 20px;
  border-bottom: 1px solid #34495e;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 24px;
  background: linear-gradient(135deg, #00bcd4, #00acc1);
  padding: 8px;
  border-radius: 8px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
}

.nav-menu {
  flex: 1;
  padding: 20px 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px 20px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.nav-item:hover {
  background-color: #34495e;
}

.nav-item.active {
  background-color: #3498db;
  border-right: 4px solid #2980b9;
}

.nav-icon {
  font-size: 18px;
}

.nav-text {
  font-size: 16px;
  font-weight: 500;
}

/* 主要内容区域 */
.main-content {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
}

/* 用户信息区域 */
.user-section {
  background: white;
  border-radius: 12px;
  padding: 30px;
  margin-bottom: 30px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  position: relative;
}

.user-info {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.user-avatar {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-icon {
  font-size: 32px;
  color: white;
}

.user-details {
  flex: 1;
}

.user-title {
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 20px 0;
}

.user-data {
  margin-bottom: 20px;
}

.info-row {
  display: flex;
  margin-bottom: 8px;
  font-size: 16px;
}

.info-label {
  color: #7f8c8d;
  min-width: 60px;
}

.info-value {
  color: #2c3e50;
  font-weight: 500;
}

.info-value.online {
  color: #27ae60;
}

.reset-password-btn {
  background: transparent;
  border: 2px solid #3498db;
  color: #3498db;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s ease;
}

.reset-password-btn:hover {
  background: #3498db;
  color: white;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-right: 800px;
  margin-top: 20px;
}

.action-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 160px;
}

.action-btn.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.action-btn.primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.action-btn.secondary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.action-btn.secondary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.action-btn.logout {
  background: #e74c3c;
  color: white;
}

.action-btn.logout:hover {
  background: #c0392b;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(231, 76, 60, 0.4);
}

/* 队列和系统状态样式保持您原有的样式 */
.queue-section {
  background: white;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  margin-bottom: 20px;
}

.queue-info {
  margin-bottom: 40px;
}

.queue-title {
  font-size: 24px;
  color: #2c3e50;
  margin: 0 0 20px 0;
  font-weight: 500;
}

.queue-number {
  font-size: 120px;
  font-weight: 700;
  color: #e74c3c;
  line-height: 1;
  margin-bottom: 20px;
  text-shadow: 2px 2px 4px rgba(231, 76, 60, 0.2);
}

.waiting-info {
  font-size: 28px;
  margin-bottom: 30px;
  color: #2c3e50;
}

.waiting-text {
  color: #2c3e50;
}

.waiting-number {
  font-size: 40px;
  font-weight: 700;
  color: #e74c3c;
  margin: 0 10px;
}

.status-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex-direction: column;
}

.status-text {
  font-size: 20px;
  color: #7f8c8d;
}

.status-text.charging {
  color: #3498db;
  font-weight: 600;
}

.estimated-time {
  font-size: 14px;
  color: #666;
  margin-top: 10px;
}

.charging-controls {
  margin-top: 20px;
}

.stop-charging-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.stop-charging-btn:hover {
  background: #c0392b;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(231, 76, 60, 0.4);
}

.charging-info {
  margin-top: 15px;
  padding: 15px;
  background: rgba(52, 152, 219, 0.1);
  border-radius: 8px;
  border: 1px solid rgba(52, 152, 219, 0.2);
}

.charging-detail {
  font-size: 14px;
  color: #2c3e50;
  margin-bottom: 5px;
}

.charging-detail:last-child {
  margin-bottom: 0;
}

.loading-dots {
  display: flex;
  gap: 4px;
  justify-content: center;
}

.dot {
  width: 8px;
  height: 8px;
  background: #7f8c8d;
  border-radius: 50%;
  animation: loading 1.4s infinite ease-in-out;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes loading {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.connection-warning {
  margin-top: 20px;
  padding: 12px 16px;
  background: rgba(255, 193, 7, 0.1);
  border: 1px solid rgba(255, 193, 7, 0.3);
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.warning-icon {
  font-size: 16px;
}

.warning-text {
  font-size: 14px;
  color: #856404;
}

.system-status {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.system-status h4 {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 15px 0;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 15px;
}

.status-item {
  text-align: center;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.status-label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.status-value {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #2c3e50;
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 400px;
  max-width: 90vw;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  animation: modalSlideIn 0.3s ease-out;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #aaa;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: #f8f9fa;
  color: #666;
}

.modal-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.form-select {
  width: 100%;
  height: 40px;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 0 12px;
  font-size: 14px;
  background: white;
  color: #333;
  outline: none;
  transition: border-color 0.2s ease;
}

.form-select:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-input-modal {
  width: 100%;
  height: 40px;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 0 12px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s ease;
}

.form-input-modal:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.password-input {
  border-radius: 25px !important;
  height: 50px !important;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #e0e0e0 !important;
  padding: 0 20px !important;
  font-size: 16px;
  color: #333;
  margin-bottom: 0;
}

.password-input::placeholder {
  color: #999;
}

.password-input:focus {
  border-color: #4CAF50 !important;
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1) !important;
  background: white;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #e9ecef;
  display: flex;
  justify-content: center;
}

.submit-btn {
  background: #4CAF50;
  color: white;
  border: none;
  padding: 12px 32px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 100px;
}

.submit-btn:hover:not(:disabled) {
  background: #45a049;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
}

.submit-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .user-section {
    flex-direction: column;
    gap: 20px;
  }

  .action-buttons {
    flex-direction: row;
    justify-content: center;
    margin-right: 0;
    margin-top: 0;
  }
}

@media (max-width: 768px) {
  .sidebar {
    width: 200px;
  }

  .main-content {
    padding: 20px;
  }

  .queue-number {
    font-size: 80px;
  }

  .waiting-number {
    font-size: 30px;
  }

  .modal-content {
    width: 350px;
    margin: 20px;
  }

  .action-buttons {
    flex-direction: column;
  }

  .charging-info {
    padding: 12px;
  }
  
  .charging-detail {
    font-size: 13px;
  }
  
  .connection-warning {
    padding: 10px 12px;
  }
  
  .warning-text {
    font-size: 13px;
  }
  
  .system-status {
    padding: 15px;
  }
  
  .status-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
  }
  
  .status-item {
    padding: 8px;
  }
  
  .status-value {
    font-size: 16px;
  }
}

@media (max-width: 480px) {
  .modal-content {
    width: 90vw;
    margin: 10px;
  }

  .modal-header {
    padding: 16px 20px;
  }

  .modal-body {
    padding: 20px;
  }

  .modal-footer {
    padding: 12px 20px;
  }
}
</style>