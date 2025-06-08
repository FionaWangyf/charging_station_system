<template>
  <el-table :data="chargingData" style="width: 100%" v-loading="loading">
    <el-table-column prop="name" label="充电桩" />

    <el-table-column label="当前状态">
      <template #default="{ row }">
        <el-tag :type="statusTagType(getStatus(row))" disable-transitions>
          {{ getStatus(row) }}
        </el-tag>
      </template>
    </el-table-column>

    <el-table-column prop="count" label="累计充电次数" />
    <el-table-column prop="duration" label="充电总时长（h）" />
    <el-table-column prop="energy" label="总充电量（度）" />

    <el-table-column label="操作">
      <template #default="{ row }">
        <el-switch
          v-model="row.power"
          :disabled="loading || (row.isFault && row.power)"
          @change="handlePowerToggle(row)"
          active-text="启动"
          inactive-text="停止"
        />
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '@/api'
import { ElMessage } from 'element-plus'

const chargingData = ref([])
const loading = ref(false)
let refreshTimer = null

// 获取充电桩状态
async function fetchPilesStatus() {
  loading.value = true
  try {
    const response = await api.admin.getPilesStatus()
    
    if (response && response.data && response.data.piles) {
      chargingData.value = response.data.piles.map(pile => ({
        name: pile.name,
        power: pile.db_status === 'available',
        isCharging: pile.current_session !== null,
        isFault: pile.db_status === 'fault',
        count: pile.statistics?.total_charges || 0,  // 注意：数据在 statistics 对象里
        duration: Number(pile.statistics?.total_power || 0).toFixed(1),
        energy: Number(pile.statistics?.total_power || 0).toFixed(1), // 这里应该是功率，不是收入
        id: pile.id
      }))
    } else {
      chargingData.value = []
      ElMessage.warning('无法获取充电桩数据')
    }
  } catch (error) {
    console.error('获取充电桩状态失败:', error)
    ElMessage.error('获取充电桩状态失败: ' + (error.message || '未知错误'))
    chargingData.value = []
  } finally {
    loading.value = false
  }
}

// 切换充电桩电源
async function handlePowerToggle(row) {
  const originalState = row.power
  
  try {
    if (row.power) {
      // 启动充电桩
      const response = await api.admin.startPile(row.id)
      if (response && response.success) {
        ElMessage.success(response.message || `充电桩 ${row.name} 已启动`)
      }
    } else {
      // 停止充电桩
      const response = await api.admin.stopPile(row.id)
      if (response && response.success) {
        ElMessage.success(`充电桩 ${row.name} 已停止`)
        // 电源关闭后必须停止充电
        row.isCharging = false
      }
    }
    
    // 延迟刷新状态，确保后端状态已更新
    setTimeout(() => {
      fetchPilesStatus()
    }, 500)
    
  } catch (error) {
    console.error('操作失败:', error)
    ElMessage.error('操作失败: ' + (error.message || '未知错误'))
    
    // 回滚状态
    row.power = originalState
  }
}

// 状态标签颜色类型
function statusTagType(status) {
  switch (status) {
    case '待启动': return 'warning'
    case '空闲': return 'info'
    case '充电中': return 'success'
    case '故障': return 'danger'
    default: return 'info'
  }
}

// 通过字段组合计算状态
function getStatus(row) {
  if (!row.power) return '待启动'
  if (row.isFault) return '故障'
  if (row.isCharging) return '充电中'
  return '空闲'
}

onMounted(() => {
  fetchPilesStatus()
  // 定时刷新（每5秒）
  refreshTimer = setInterval(fetchPilesStatus, 5000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<style scoped>
:deep(.el-switch__label) {
  font-size: 12px;
}

:deep(.el-tag) {
  font-weight: 500;
}
</style>