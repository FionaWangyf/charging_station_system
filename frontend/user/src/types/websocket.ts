// WebSocket 事件类型定义
export interface WebSocketEvents {
    // 连接事件
    connected: { message: string; sid: string }
    room_joined: { message: string; room: string; user_id: string }
    room_left: { message: string; room: string; user_id: string }
    error: { message: string }
    
    // 排队状态更新
    queue_status_update: {
      user_id: string
      queue_number: string
      waiting_count: number
      status: 'waiting' | 'charging' | 'completed' | 'cancelled'
      estimated_wait_time?: number
    }
    
    // 充电状态更新
    charging_status_update: {
      user_id: string
      session_id: string
      pile_id: string
      status: 'assigned' | 'charging' | 'completed' | 'fault'
      power_consumed?: number
      charging_duration?: number
      estimated_completion?: string
    }
    
    // 系统状态更新
    system_status_update: {
      total_queuing: number
      total_charging: number
      available_piles: number
      system_load: number
    }
    
    // 通知消息
    notification: {
      type: 'info' | 'warning' | 'error' | 'success'
      title: string
      message: string
      timestamp: string
    }
    
    // 心跳检测
    pong: { timestamp: string }
  }
  
  // WebSocket 连接状态
  export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error'
  
  // 用户排队信息
  export interface QueueInfo {
    currentNumber: string
    waitingCount: number
    status: string
    isStopped: boolean
    estimatedWaitTime?: number
    position?: number
  }
  
  // 充电会话信息
  export interface ChargingSession {
    sessionId: string
    pileId: string
    startTime: string
    status: 'assigned' | 'charging' | 'completed' | 'fault'
    powerConsumed: number
    chargingDuration: number
    estimatedCompletion?: string
  }
  
  // 系统通知
  export interface SystemNotification {
    id: string
    type: 'info' | 'warning' | 'error' | 'success'
    title: string
    message: string
    timestamp: string
    read: boolean
  }