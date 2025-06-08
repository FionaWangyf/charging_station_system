import { io, Socket } from 'socket.io-client'
import type { WebSocketEvents, WebSocketStatus } from '@/types/websocket'

export class WebSocketService {
  private socket: Socket | null = null
  private status: WebSocketStatus = 'disconnected'
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectTimeout: number | null = null
  private userId: string | null = null
  private eventListeners: Map<string, Function[]> = new Map()

  constructor() {
    this.initializeSocket()
  }

  /**
   * 初始化 WebSocket 连接
   */
  private initializeSocket() {
    try {
      // 获取后端服务器地址
      const serverUrl = import.meta.env.PROD 
        ? window.location.origin  // 生产环境使用当前域名
        : 'http://localhost:5001'  // 开发环境使用后端地址

      console.log('🔌 正在连接 WebSocket 服务器:', serverUrl)

      this.socket = io(serverUrl, {
        transports: ['websocket', 'polling'],
        autoConnect: false,
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: 1000,
        timeout: 10000,
        forceNew: true
      })

      this.setupEventHandlers()
    } catch (error) {
      console.error('❌ WebSocket 初始化失败:', error)
      this.status = 'error'
    }
  }

// 在 utils/websocket.ts 中修复事件监听

    /**
     * 设置 WebSocket 事件处理器
     */
    private setupEventHandlers() {
        if (!this.socket) return
    
        // 连接成功
        this.socket.on('connect', () => {
        console.log(`✅ WebSocket 连接成功 (标签页: ${this.tabId})`)
        this.status = 'connected'
        this.reconnectAttempts = 0
        this.clearReconnectTimeout()
        this.emit('statusChange', this.status)
        
        // 如果有用户ID，自动加入用户房间
        if (this.userId) {
            this.joinUserRoom(this.userId)
        }
        })
    
        // 连接失败
        this.socket.on('connect_error', (error) => {
        console.error(`❌ WebSocket 连接失败 (标签页: ${this.tabId}):`, error)
        this.status = 'error'
        this.emit('statusChange', this.status)
        this.handleReconnect()
        })
    
        // 断开连接
        this.socket.on('disconnect', (reason) => {
        console.warn(`⚠️ WebSocket 连接断开 (标签页: ${this.tabId}):`, reason)
        this.status = 'disconnected'
        this.emit('statusChange', this.status)
        
        if (reason === 'io server disconnect') {
            // 服务器主动断开，需要手动重连
            this.handleReconnect()
        }
        })
    
        // 监听服务器事件
        this.socket.on('connected', (data) => {
        console.log(`🎉 服务器确认连接 (标签页: ${this.tabId}):`, data)
        this.emit('connected', data)
        })
    
        this.socket.on('room_joined', (data) => {
        console.log(`🏠 加入房间成功 (标签页: ${this.tabId}):`, data)
        this.emit('room_joined', data)
        })
    
        // 修复：监听正确的事件名称
        this.socket.on('status_update', (data) => {
        console.log(`🖥️ 系统状态更新 (标签页: ${this.tabId}):`, data)
        this.emit('system_status_update', data)  // 转换为前端期望的事件名
        })
    
        // 排队状态更新（可能需要后端添加）
        this.socket.on('queue_status_update', (data) => {
        console.log(`📊 排队状态更新 (标签页: ${this.tabId}):`, data)
        this.emit('queue_status_update', data)
        })
    
        // 充电状态更新
        this.socket.on('charging_status_update', (data) => {
        console.log(`⚡ 充电状态更新 (标签页: ${this.tabId}):`, data)
        this.emit('charging_status_update', data)
        })
    
        // 通知消息
        this.socket.on('notification', (data) => {
        console.log(`📢 收到通知 (标签页: ${this.tabId}):`, data)
        this.emit('notification', data)
        })
    
        // 错误处理
        this.socket.on('error', (data) => {
        console.error(`❌ 服务器错误 (标签页: ${this.tabId}):`, data)
        this.emit('error', data)
        })
    
        // 心跳响应
        this.socket.on('pong', (data) => {
        console.log(`🏓 心跳响应 (标签页: ${this.tabId}):`, data)
        this.emit('pong', data)
        })
    }

  /**
   * 连接到 WebSocket 服务器
   */
  connect(userId?: string) {
    if (userId) {
      this.userId = userId
    }

    if (!this.socket) {
      this.initializeSocket()
    }

    if (this.socket && this.status !== 'connected') {
      console.log('🔄 正在连接 WebSocket...')
      this.status = 'connecting'
      this.emit('statusChange', this.status)
      this.socket.connect()
    }
  }

  /**
   * 断开 WebSocket 连接
   */
  disconnect() {
    this.clearReconnectTimeout()
    
    if (this.socket && this.socket.connected) {
      console.log('🔌 断开 WebSocket 连接')
      this.socket.disconnect()
    }
    
    this.status = 'disconnected'
    this.emit('statusChange', this.status)
  }

  /**
   * 加入用户房间
   */
  joinUserRoom(userId: string) {
    if (this.socket && this.socket.connected) {
      this.userId = userId
      this.socket.emit('join_user_room', { user_id: userId })
      console.log('🏠 请求加入用户房间:', userId)
    }
  }

  /**
   * 离开用户房间
   */
  leaveUserRoom(userId: string) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('leave_user_room', { user_id: userId })
      console.log('🏠 请求离开用户房间:', userId)
    }
  }

  /**
   * 请求系统状态更新
   */
  requestSystemStatus() {
    if (this.socket && this.socket.connected) {
      this.socket.emit('request_system_status')
      console.log('📊 请求系统状态更新')
    }
  }

  /**
   * 发送心跳检测
   */
  ping() {
    if (this.socket && this.socket.connected) {
      this.socket.emit('ping')
      console.log('🏓 发送心跳检测')
    }
  }

  /**
   * 处理重连逻辑
   */
  private handleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('❌ 达到最大重连次数，停止重连')
      this.status = 'error'
      this.emit('statusChange', this.status)
      return
    }

    this.reconnectAttempts++
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)
    
    console.log(`🔄 第 ${this.reconnectAttempts} 次重连尝试，${delay}ms 后重连...`)
    
    this.reconnectTimeout = window.setTimeout(() => {
      if (this.status !== 'connected') {
        this.connect()
      }
    }, delay)
  }

  /**
   * 清除重连定时器
   */
  private clearReconnectTimeout() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
  }

  /**
   * 添加事件监听器
   */
  on<K extends keyof WebSocketEvents>(event: K, callback: (data: WebSocketEvents[K]) => void): void
  on(event: 'statusChange', callback: (status: WebSocketStatus) => void): void
  on(event: string, callback: Function): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, [])
    }
    this.eventListeners.get(event)!.push(callback)
  }

  /**
   * 移除事件监听器
   */
  off(event: string, callback?: Function) {
    const listeners = this.eventListeners.get(event)
    if (listeners) {
      if (callback) {
        const index = listeners.indexOf(callback)
        if (index > -1) {
          listeners.splice(index, 1)
        }
      } else {
        this.eventListeners.set(event, [])
      }
    }
  }

  /**
   * 触发事件
   */
  private emit(event: string, data?: any) {
    const listeners = this.eventListeners.get(event)
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`❌ WebSocket 事件处理错误 [${event}]:`, error)
        }
      })
    }
  }

  /**
   * 获取连接状态
   */
  getStatus(): WebSocketStatus {
    return this.status
  }

  /**
   * 获取用户ID
   */
  getUserId(): string | null {
    return this.userId
  }

  /**
   * 检查是否已连接
   */
  isConnected(): boolean {
    return this.status === 'connected' && this.socket?.connected === true
  }

  /**
   * 销毁 WebSocket 服务
   */
  destroy() {
    console.log('🔥 销毁 WebSocket 服务')
    this.disconnect()
    this.eventListeners.clear()
    this.socket = null
    this.userId = null
  }
}

// 创建全局 WebSocket 服务实例
export const websocketService = new WebSocketService()