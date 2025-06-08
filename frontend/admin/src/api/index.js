// 基础API配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

// 通用请求函数
async function request(url, options = {}) {
  const config = {
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include', // 支持session
    ...options
  }

  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body)
  }

  const response = await fetch(`${API_BASE_URL}${url}`, config)
  const data = await response.json()
  
  if (!response.ok) {
    throw new Error(data.message || '请求失败')
  }
  
  return data
}

// API接口
export const api = {
  // 管理员API
  admin: {
    // 获取所有充电桩状态
    getPilesStatus: () => request('/api/admin/piles/status'),
    // 启动充电桩
    startPile: (pileId) => request('/api/admin/pile/start', {
      method: 'POST',
      body: { pile_id: pileId }
    }),
    // 停止充电桩
    stopPile: (pileId, force = false) => request('/api/admin/pile/stop', {
      method: 'POST',
      body: { pile_id: pileId, force }
    }),
    // 获取队列信息
    getQueueInfo: () => request('/api/admin/queue/info'),
    // 获取系统概览
    getOverview: () => request('/api/admin/overview')
  },
  
  // 统计API
  statistics: {
    // 获取概览统计
    getOverview: () => request('/api/statistics/overview'),
    // 获取日统计
    getDaily: (days = 7) => request(`/api/statistics/daily?days=${days}`),
    // 获取充电桩使用统计
    getPileUsage: () => request('/api/statistics/pile-usage'),
    // 获取时段统计
    getTimePeriod: () => request('/api/statistics/time-period')
  }
}