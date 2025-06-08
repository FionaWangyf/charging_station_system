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

    <el-table-column label="启动">
      <template #default="{ row }">
        <el-switch
          v-model="row.power"
          :disabled="row.isFault"
          @change="handlePowerToggle(row)"
        />
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '@/api'
import { ElMessage } from 'element-plus'

const chargingData = ref([])
const loading = ref(false)

// 获取充电桩状态
async function fetchPilesStatus() {
  loading.value = true
  try {
    const response = await api.admin.getPilesStatus()
    chargingData.value = response.data.piles.map(pile => ({
      name: pile.name,
      power: pile.db_status === 'available',
      isCharging: pile.current_session !== null,
      isFault: pile.db_status === 'fault',
      count: pile.total_charges || 0,
      duration: Number(pile.total_power || 0).toFixed(1),
      energy: Number(pile.total_revenue || 0).toFixed(1),
      id: pile.id
    }))
  } catch (error) {
    ElMessage.error('获取充电桩状态失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

// 切换充电桩电源
async function handlePowerToggle(row) {
  try {
    if (row.power) {
      await api.admin.startPile(row.id)
      ElMessage.success(`充电桩 ${row.name} 已启动`)
    } else {
      await api.admin.stopPile(row.id)
      ElMessage.success(`充电桩 ${row.name} 已停止`)
      // 电源关闭后必须停止充电
      row.isCharging = false
    }
    // 重新获取状态
    await fetchPilesStatus()
  } catch (error) {
    ElMessage.error('操作失败: ' + error.message)
    // 回滚状态
    row.power = !row.power
  }
}

// 状态标签颜色类型
function statusTagType(status) {
  switch (status) {
    case '待启动': return 'warning'
    case '空闲': return 'info'
    case '充电中': return 'success'
    case '故障': return 'danger'
    default: return ''
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
  // 定时刷新
  setInterval(fetchPilesStatus, 5000)
})
</script>
