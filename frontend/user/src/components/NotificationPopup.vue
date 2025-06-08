<template>
  <Transition name="notification">
    <div v-if="notification" class="notification-overlay" @click="handleOverlayClick">
      <div class="notification-popup" :class="notificationClass" @click.stop>
        <div class="notification-icon">
          {{ notificationIcon }}
        </div>
        
        <div class="notification-content">
          <h3 class="notification-title">{{ notification.title }}</h3>
          <p class="notification-message">{{ notification.message }}</p>
          <span class="notification-time">{{ formatTime(notification.timestamp) }}</span>
        </div>
        
        <button class="notification-close" @click="$emit('close')">
          ×
        </button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SystemNotification } from '@/types/websocket'

// Props
interface Props {
  notification: SystemNotification | null
}

const props = defineProps<Props>()

// Emits
defineEmits<{
  close: []
}>()

// 计算属性
const notificationClass = computed(() => {
  if (!props.notification) return ''
  
  return `notification-${props.notification.type}`
})

const notificationIcon = computed(() => {
  if (!props.notification) return ''
  
  switch (props.notification.type) {
    case 'success':
      return '✅'
    case 'info':
      return 'ℹ️'
    case 'warning':
      return '⚠️'
    case 'error':
      return '❌'
    default:
      return 'ℹ️'
  }
})

// 方法
const formatTime = (timestamp: string) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

const handleOverlayClick = (event: MouseEvent) => {
  // 点击遮罩层关闭通知
  if (event.target === event.currentTarget) {
    emit('close')
  }
}

// 自动关闭定时器
let autoCloseTimer: number | null = null

const startAutoCloseTimer = () => {
  if (autoCloseTimer) {
    clearTimeout(autoCloseTimer)
  }
  
  // 5秒后自动关闭
  autoCloseTimer = window.setTimeout(() => {
    emit('close')
  }, 5000)
}

// 监听通知变化
watch(() => props.notification, (newNotification) => {
  if (newNotification) {
    startAutoCloseTimer()
  } else {
    if (autoCloseTimer) {
      clearTimeout(autoCloseTimer)
      autoCloseTimer = null
    }
  }
})

// 清理定时器
onUnmounted(() => {
  if (autoCloseTimer) {
    clearTimeout(autoCloseTimer)
  }
})
</script>

<style scoped>
.notification-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  z-index: 10000;
  padding-top: 80px;
}

.notification-popup {
  background: white;
  border-radius: 12px;
  padding: 20px;
  min-width: 320px;
  max-width: 500px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: flex-start;
  gap: 16px;
  position: relative;
  margin: 0 20px;
  border-left: 4px solid;
}

.notification-success {
  border-left-color: #4CAF50;
  background: linear-gradient(135deg, #f8fff8 0%, #f0f8f0 100%);
}

.notification-info {
  border-left-color: #2196F3;
  background: linear-gradient(135deg, #f8fcff 0%, #f0f6ff 100%);
}

.notification-warning {
  border-left-color: #FF9800;
  background: linear-gradient(135deg, #fffbf8 0%, #fff4e6 100%);
}

.notification-error {
  border-left-color: #f44336;
  background: linear-gradient(135deg, #fff8f8 0%, #ffeaea 100%);
}

.notification-icon {
  font-size: 24px;
  flex-shrink: 0;
  margin-top: 2px;
}

.notification-content {
  flex: 1;
}

.notification-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 8px 0;
  line-height: 1.4;
}

.notification-message {
  font-size: 14px;
  color: #555;
  margin: 0 0 8px 0;
  line-height: 1.5;
}

.notification-time {
  font-size: 12px;
  color: #999;
}

.notification-close {
  position: absolute;
  top: 8px;
  right: 8px;
  background: none;
  border: none;
  font-size: 20px;
  color: #999;
  cursor: pointer;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.notification-close:hover {
  background: rgba(0, 0, 0, 0.1);
  color: #666;
}

/* 动画效果 */
.notification-enter-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.notification-leave-active {
  transition: all 0.3s ease-in;
}

.notification-enter-from {
  opacity: 0;
  transform: translateY(-50px) scale(0.9);
}

.notification-leave-to {
  opacity: 0;
  transform: translateY(-20px) scale(0.95);
}

.notification-enter-from .notification-overlay {
  background: rgba(0, 0, 0, 0);
}

.notification-leave-to .notification-overlay {
  background: rgba(0, 0, 0, 0);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .notification-overlay {
    padding-top: 60px;
  }
  
  .notification-popup {
    min-width: auto;
    width: calc(100% - 40px);
    max-width: none;
    padding: 16px;
    margin: 0 20px;
  }
  
  .notification-icon {
    font-size: 20px;
  }
  
  .notification-title {
    font-size: 15px;
  }
  
  .notification-message {
    font-size: 13px;
  }
}
</style>