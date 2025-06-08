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
        <div class="nav-item" @click="$emit('switchToMain')">
          <span class="nav-icon">🏠</span>
          <span class="nav-text">主页</span>
        </div>
        <div class="nav-item active">
          <span class="nav-icon">⚡</span>
          <span class="nav-text">充电详单</span>
        </div>
      </nav>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content">
      <div class="page-header">
        <h1 class="page-title">查看充电详单</h1>
      </div>

      <!-- 充电详单列表 -->
      <div class="details-container">
        <div v-for="order in chargingOrders" :key="order.id" class="order-card">
          <h3 class="order-title">订单信息</h3>

          <div class="order-details">
            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">详单编号：</span>
                <span class="detail-value">{{ order.orderNumber }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">详单生成时间：</span>
                <span class="detail-value">{{ order.generateTime }}</span>
              </div>
            </div>

            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">充电桩编号：</span>
                <span class="detail-value">{{ order.stationNumber }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">启动时间：</span>
                <span class="detail-value">{{ order.startTime }}</span>
              </div>
            </div>

            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">充电电量：</span>
                <span class="detail-value">{{ order.chargeAmount }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">停止时间：</span>
                <span class="detail-value">{{ order.endTime }}</span>
              </div>
            </div>

            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">充电时长：</span>
                <span class="detail-value">{{ order.chargeDuration }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">充电费用（元）：</span>
                <span class="detail-value">{{ order.chargeFee }}</span>
              </div>
            </div>

            <div class="detail-row">
              <div class="detail-item"></div>
              <div class="detail-item">
                <span class="detail-label">服务费用（元）：</span>
                <span class="detail-value">{{ order.serviceFee }}</span>
              </div>
            </div>

            <div class="detail-row">
              <div class="detail-item"></div>
              <div class="detail-item total-row">
                <span class="detail-label">总费用（元）：</span>
                <span class="detail-value total-value">{{ order.totalFee }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

// 定义事件
defineEmits<{
  switchToMain: []
}>()

// 充电订单数据
interface ChargingOrder {
  id: number
  orderNumber: string
  generateTime: string
  stationNumber: string
  startTime: string
  endTime: string
  chargeAmount: number
  chargeDuration: number
  chargeFee: number
  serviceFee: number
  totalFee: number
}

const chargingOrders = ref<ChargingOrder[]>([])

// 组件挂载时获取充电详单数据
onMounted(() => {
  fetchChargingDetails()
})

// 获取充电详单数据
const fetchChargingDetails = async () => {
  try {
    // 这里应该调用后端API获取充电详单
    // const response = await fetch('/api/charging/orders', {
    //   headers: {
    //     'Authorization': `Bearer ${localStorage.getItem('token')}`
    //   }
    // })
    // const data = await response.json()
    // chargingOrders.value = data.orders

    // 模拟数据
    chargingOrders.value = [
      {
        id: 1,
        orderNumber: '1111222222',
        generateTime: '2019-05-21 12:00:00',
        stationNumber: 'F1',
        startTime: '2019-05-21 12:00:00',
        endTime: '2019-05-21 14:00:00',
        chargeAmount: 100,
        chargeDuration: 120,
        chargeFee: 100,
        serviceFee: 10,
        totalFee: 110
      },
      {
        id: 2,
        orderNumber: '1111222322',
        generateTime: '2019-05-20 12:00:00',
        stationNumber: 'F1',
        startTime: '2019-05-20 12:00:00',
        endTime: '2019-05-20 14:00:00',
        chargeAmount: 80,
        chargeDuration: 100,
        chargeFee: 80,
        serviceFee: 8,
        totalFee: 88
      },
      {
        id: 3,
        orderNumber: '1111222423',
        generateTime: '2019-05-19 12:00:00',
        stationNumber: 'F2',
        startTime: '2019-05-19 10:00:00',
        endTime: '2019-05-19 12:30:00',
        chargeAmount: 120,
        chargeDuration: 150,
        chargeFee: 120,
        serviceFee: 12,
        totalFee: 132
      },
      {
        id: 4,
        orderNumber: '1111222524',
        generateTime: '2019-05-18 12:00:00',
        stationNumber: 'F1',
        startTime: '2019-05-18 14:00:00',
        endTime: '2019-05-18 16:00:00',
        chargeAmount: 90,
        chargeDuration: 110,
        chargeFee: 90,
        serviceFee: 9,
        totalFee: 99
      }
    ]
  } catch (error) {
    console.error('获取充电详单失败:', error)
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

.page-header {
  margin-bottom: 30px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

/* 充电详单列表 */
.details-container {
  max-height: calc(100vh - 150px);
  overflow-y: auto;
  padding-right: 10px;
}

.details-container::-webkit-scrollbar {
  width: 8px;
}

.details-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.details-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.details-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.order-card {
  background: white;
  border-radius: 12px;
  padding: 25px;
  margin-bottom: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid #e9ecef;
}

.order-title {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 20px 0;
  padding-bottom: 10px;
  border-bottom: 2px solid #f8f9fa;
}

.order-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}

.detail-item {
  flex: 1;
  display: flex;
  align-items: center;
}

.detail-item:first-child {
  justify-content: flex-start;
}

.detail-item:last-child {
  justify-content: flex-end;
}

.detail-label {
  font-size: 14px;
  color: #7f8c8d;
  margin-right: 8px;
  min-width: 120px;
}

.detail-value {
  font-size: 14px;
  color: #2c3e50;
  font-weight: 500;
}

.total-row {
  border-top: 1px solid #e9ecef;
  padding-top: 10px;
  margin-top: 5px;
}

.total-row .detail-label {
  font-weight: 600;
  color: #2c3e50;
}

.total-value {
  font-weight: 700;
  color: #e74c3c;
  font-size: 16px;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .detail-row {
    flex-direction: column;
    gap: 8px;
  }

  .detail-item {
    justify-content: flex-start !important;
  }
}

@media (max-width: 768px) {
  .sidebar {
    width: 200px;
  }

  .main-content {
    padding: 20px;
  }

  .order-card {
    padding: 20px;
  }

  .detail-label {
    min-width: 100px;
    font-size: 13px;
  }

  .detail-value {
    font-size: 13px;
  }
}

@media (max-width: 480px) {
  .main-content {
    padding: 15px;
  }

  .order-card {
    padding: 15px;
  }

  .page-title {
    font-size: 24px;
  }
}
</style>
