import { ref, reactive, onMounted, onUnmounted, computed, readonly } from 'vue'
import { websocketService } from '@/utils/websocket'
import type { 
  WebSocketStatus, 
  QueueInfo, 
  ChargingSession, 
  SystemNotification,
  WebSocketEvents 
} from '@/types/websocket'

/**
 * WebSocket 组合式 API（改进版本）
 */
export function useWebSocket() {
  // 响应式状态
  const status = ref<WebSocketStatus>('disconnected')
  const isConnected = computed(() => status.value === 'connected')
  const isConnecting = computed(() => status.value === 'connecting')
  
  // 排队信息
  const queueInfo = reactive<QueueInfo>({
    currentNumber: '--',
    waitingCount: 0,
    status: '未排队',
    isStopped: true,
    estimatedWaitTime: undefined,
    position: undefined
  })

  // 充电会话信息
  const chargingSession = ref<ChargingSession | null>(null)

  // 系统通知列表
  const notifications = ref<SystemNotification[]>([])
  const unreadNotificationCount = computed(() => 
    notifications.value.filter(n => !n.read).length
  )

  // 系统状态
  const systemStatus = reactive({
    totalQueuing: 0,
    totalCharging: 0,
    availablePiles: 0,
    systemLoad: 0,
    onlinePiles: 0,
    waitingCars: 0,
    chargingCars: 0
  })

  // 连接状态监听器
  const statusChangeHandler = (newStatus: WebSocketStatus) => {
    status.value = newStatus
    console.log('📡 WebSocket 状态变化:', newStatus)
    
    // 如果连接成功，立即获取数据
    if (newStatus === 'connected') {
      setTimeout(() => {
        fetchSystemStatusViaHTTP()
        fetchUserStatusViaHTTP()
      }, 500)
    }
  }

  // 排队状态更新处理器
  const queueStatusUpdateHandler = (data: WebSocketEvents['queue_status_update']) => {
    console.log('📊 排队状态更新:', data)
    
    queueInfo.currentNumber = data.queue_number
    queueInfo.waitingCount = data.waiting_count
    queueInfo.estimatedWaitTime = data.estimated_wait_time
    queueInfo.isStopped = false

    // 根据状态设置显示文本
    switch (data.status) {
      case 'waiting':
        queueInfo.status = data.waiting_count === 0 ? '即将开始充电' : '排队中，请等候'
        break
      case 'charging':
        queueInfo.status = '正在充电'
        queueInfo.waitingCount = 0
        break
      case 'completed':
        queueInfo.status = '充电完成'
        queueInfo.isStopped = true
        break
      case 'cancelled':
        queueInfo.status = '已取消'
        queueInfo.isStopped = true
        break
      default:
        queueInfo.status = '未知状态'
    }
  }

  // 充电状态更新处理器
  const chargingStatusUpdateHandler = (data: WebSocketEvents['charging_status_update']) => {
    console.log('⚡ 充电状态更新:', data)
    
    chargingSession.value = {
      sessionId: data.session_id,
      pileId: data.pile_id,
      startTime: new Date().toISOString(),
      status: data.status,
      powerConsumed: data.power_consumed || 0,
      chargingDuration: data.charging_duration || 0,
      estimatedCompletion: data.estimated_completion
    }

    // 更新排队信息以反映充电状态
    if (data.status === 'charging') {
      queueInfo.waitingCount = 0
      queueInfo.status = '正在充电'
    } else if (data.status === 'completed') {
      queueInfo.status = '充电完成'
      queueInfo.isStopped = true
    } else if (data.status === 'fault') {
      queueInfo.status = '充电桩故障'
      addNotification('error', '充电桩故障', '您的充电桩出现故障，请等待重新分配')
    }
  }

  // 在 useWebSocket.ts 中修复系统状态更新处理器

// 系统状态更新处理器（修复版本）
const systemStatusUpdateHandler = (data: any) => {
    console.log('🖥️ 系统状态更新:', data)
    
    // 处理不同的数据格式
    if (data.total_queuing !== undefined) {
      systemStatus.totalQueuing = data.total_queuing
      systemStatus.totalCharging = data.total_charging
      systemStatus.availablePiles = data.available_piles
      systemStatus.systemLoad = data.system_load
    }
    
    // 处理等候区数据
    if (data.station_waiting_area) {
      systemStatus.waitingCars = data.station_waiting_area.total || 0
    }
    
    // 处理调度队列数据
    if (data.engine_dispatch_queues) {
      const queues = data.engine_dispatch_queues
      systemStatus.totalQueuing = (queues.fast_count || 0) + (queues.trickle_count || 0)
    }
    
    // 处理充电桩数据（关键修复）
    if (data.charging_piles) {
      const piles = Object.values(data.charging_piles) as any[]
      console.log('🔧 分析充电桩状态:', piles)
      
      let availableCount = 0
      let onlineCount = 0
      let chargingCount = 0
      
      piles.forEach((pile, index) => {
        const pileId = Object.keys(data.charging_piles)[index]
        console.log(`📍 充电桩 ${pileId}:`, pile)
        
        // 检查多种可能的状态字段
        const status = pile.status || pile.db_status || pile.app_status || pile.state
        const isOccupied = pile.occupied || pile.is_occupied || pile.current_session
        
        console.log(`   状态: ${status}, 占用: ${isOccupied}`)
        
        // 统计在线充电桩
        if (status !== 'offline' && status !== 'fault' && status !== 'error') {
          onlineCount++
          
          // 统计可用充电桩（在线且未被占用）
          if (!isOccupied && (
            status === 'available' || 
            status === 'idle' || 
            status === 'ready' ||
            status === 'online' ||
            status === null ||
            status === undefined
          )) {
            availableCount++
            console.log(`   ✅ 充电桩 ${pileId} 可用`)
          } else if (isOccupied || status === 'occupied' || status === 'charging' || status === 'busy') {
            chargingCount++
            console.log(`   ⚡ 充电桩 ${pileId} 充电中`)
          }
        } else {
          console.log(`   ❌ 充电桩 ${pileId} 离线或故障`)
        }
      })
      
      // 更新状态
      systemStatus.availablePiles = availableCount
      systemStatus.onlinePiles = onlineCount
      systemStatus.chargingCars = chargingCount
      
      console.log(`📊 充电桩统计更新: 在线${onlineCount}, 可用${availableCount}, 充电中${chargingCount}`)
      
      // 如果仍然是0，使用保守估计
      if (availableCount === 0 && onlineCount > 0) {
        console.log('⚠️ 检测到在线充电桩但无可用桩，使用保守估计')
        systemStatus.availablePiles = Math.max(1, onlineCount - chargingCount)
      }
    }
    
    // 兼容其他格式
    if (data.online_piles !== undefined) {
      systemStatus.onlinePiles = data.online_piles
    }
    if (data.waiting_cars !== undefined) {
      systemStatus.waitingCars = data.waiting_cars
    }
    if (data.charging_cars !== undefined) {
      systemStatus.chargingCars = data.charging_cars
    }
  }

  // 通知处理器
  const notificationHandler = (data: WebSocketEvents['notification']) => {
    console.log('📢 收到通知:', data)
    addNotification(data.type, data.title, data.message)
  }

  // 错误处理器
  const errorHandler = (data: WebSocketEvents['error']) => {
    console.error('❌ WebSocket 错误:', data)
    addNotification('error', '系统错误', data.message)
  }

  // HTTP API 获取系统状态
  const fetchSystemStatusViaHTTP = async () => {
    try {
      console.log('🌐 通过 HTTP API 获取系统状态...')
      const response = await fetch('/api/charging/system-status')
      
      if (response.ok) {
        const result = await response.json()
        if (result.success && result.data) {
          console.log('✅ HTTP API 系统状态获取成功:', result.data)
          systemStatusUpdateHandler(result.data)
        }
      }
    } catch (error) {
      console.error('❌ HTTP API 获取系统状态失败:', error)
    }
  }

  // HTTP API 获取用户状态
  const fetchUserStatusViaHTTP = async () => {
    try {
      console.log('🌐 通过 HTTP API 获取用户状态...')
      const response = await fetch('/api/charging/status', {
        credentials: 'include'
      })
      
      if (response.ok) {
        const result = await response.json()
        if (result.success && result.data) {
          console.log('✅ HTTP API 用户状态获取成功:', result.data)
          
          // 处理用户排队信息
          if (result.data.queue_info) {
            const queueData = result.data.queue_info
            queueInfo.currentNumber = queueData.queue_number || '--'
            queueInfo.waitingCount = queueData.waiting_count || 0
            queueInfo.status = queueData.status || '未排队'
            queueInfo.isStopped = queueData.waiting_count === undefined
          }
          
          // 处理充电会话信息
          if (result.data.current_session) {
            const sessionData = result.data.current_session
            chargingSession.value = {
              sessionId: sessionData.session_id,
              pileId: sessionData.pile_id,
              startTime: sessionData.start_time,
              status: sessionData.status,
              powerConsumed: sessionData.power_consumed || 0,
              chargingDuration: sessionData.charging_duration || 0,
              estimatedCompletion: sessionData.estimated_completion
            }
          }
        }
      }
    } catch (error) {
      console.error('❌ HTTP API 获取用户状态失败:', error)
    }
  }

  /**
   * 连接 WebSocket
   */
  const connect = (userId?: string) => {
    websocketService.connect(userId)
  }

  /**
   * 断开 WebSocket
   */
  const disconnect = () => {
    websocketService.disconnect()
  }

  /**
   * 加入用户房间
   */
  const joinUserRoom = (userId: string) => {
    websocketService.joinUserRoom(userId)
  }

  /**
   * 请求系统状态更新
   */
  const requestSystemStatus = () => {
    if (websocketService.isConnected()) {
      websocketService.requestSystemStatus()
    } else {
      // WebSocket 未连接时，使用 HTTP API
      fetchSystemStatusViaHTTP()
      fetchUserStatusViaHTTP()
    }
  }

  /**
   * 发送心跳检测
   */
  const ping = () => {
    websocketService.ping()
  }

  /**
   * 添加通知
   */
  const addNotification = (
    type: SystemNotification['type'], 
    title: string, 
    message: string
  ) => {
    const notification: SystemNotification = {
      id: Date.now().toString(),
      type,
      title,
      message,
      timestamp: new Date().toISOString(),
      read: false
    }
    
    notifications.value.unshift(notification)
    
    // 限制通知数量
    if (notifications.value.length > 50) {
      notifications.value = notifications.value.slice(0, 50)
    }
  }

  /**
   * 标记通知为已读
   */
  const markNotificationAsRead = (notificationId: string) => {
    const notification = notifications.value.find(n => n.id === notificationId)
    if (notification) {
      notification.read = true
    }
  }

  /**
   * 标记所有通知为已读
   */
  const markAllNotificationsAsRead = () => {
    notifications.value.forEach(n => {
      n.read = true
    })
  }

  /**
   * 删除通知
   */
  const removeNotification = (notificationId: string) => {
    const index = notifications.value.findIndex(n => n.id === notificationId)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  /**
   * 清空所有通知
   */
  const clearAllNotifications = () => {
    notifications.value = []
  }

  /**
   * 重置排队信息
   */
  const resetQueueInfo = () => {
    queueInfo.currentNumber = '--'
    queueInfo.waitingCount = 0
    queueInfo.status = '未排队'
    queueInfo.isStopped = true
    queueInfo.estimatedWaitTime = undefined
    queueInfo.position = undefined
  }

  /**
   * 重置充电会话
   */
  const resetChargingSession = () => {
    chargingSession.value = null
  }

  // 定期刷新数据（当 WebSocket 未连接时）
  let refreshInterval: number | null = null

  const startPeriodicRefresh = () => {
    if (refreshInterval) clearInterval(refreshInterval)
    
    refreshInterval = window.setInterval(() => {
      if (!isConnected.value) {
        console.log('🔄 WebSocket 未连接，通过 HTTP API 刷新数据...')
        fetchSystemStatusViaHTTP()
        fetchUserStatusViaHTTP()
      }
    }, 10000) // 每10秒刷新一次
  }

  const stopPeriodicRefresh = () => {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }

  // 生命周期钩子
  onMounted(() => {
    // 注册事件监听器
    websocketService.on('statusChange', statusChangeHandler)
    websocketService.on('queue_status_update', queueStatusUpdateHandler)
    websocketService.on('charging_status_update', chargingStatusUpdateHandler)
    websocketService.on('system_status_update', systemStatusUpdateHandler)
    websocketService.on('notification', notificationHandler)
    websocketService.on('error', errorHandler)

    // 获取当前状态
    status.value = websocketService.getStatus()
    
    // 立即获取一次数据
    setTimeout(() => {
      fetchSystemStatusViaHTTP()
      fetchUserStatusViaHTTP()
    }, 1000)
    
    // 开始定期刷新
    startPeriodicRefresh()
  })

  onUnmounted(() => {
    // 移除事件监听器
    websocketService.off('statusChange', statusChangeHandler)
    websocketService.off('queue_status_update', queueStatusUpdateHandler)
    websocketService.off('charging_status_update', chargingStatusUpdateHandler)
    websocketService.off('system_status_update', systemStatusUpdateHandler)
    websocketService.off('notification', notificationHandler)
    websocketService.off('error', errorHandler)
    
    // 停止定期刷新
    stopPeriodicRefresh()
  })

  return {
    // 状态
    status: readonly(status),
    isConnected,
    isConnecting,
    
    // 数据
    queueInfo: readonly(queueInfo),
    chargingSession: readonly(chargingSession),
    notifications: readonly(notifications),
    unreadNotificationCount,
    systemStatus: readonly(systemStatus),
    
    // 方法
    connect,
    disconnect,
    joinUserRoom,
    requestSystemStatus,
    ping,
    
    // HTTP API 方法
    fetchSystemStatusViaHTTP,
    fetchUserStatusViaHTTP,
    
    // 通知管理
    addNotification,
    markNotificationAsRead,
    markAllNotificationsAsRead,
    removeNotification,
    clearAllNotifications,
    
    // 数据重置
    resetQueueInfo,
    resetChargingSession
  }
}