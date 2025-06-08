<template>
  <el-table :data="chargingData" style="width: 100%">
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
import { ref } from 'vue'

// 这里是示例数据
const chargingData = ref([
  { name: '快充桩A', power: true, isCharging: true, isFault: false, count: 15, duration: 6.5, energy: 12.2 },
  { name: '快充桩B', power: false, isCharging: false, isFault: false, count: 10, duration: 4.0, energy: 10.0 },
  { name: '慢充桩C', power: true, isCharging: false, isFault: false, count: 12, duration: 5.5, energy: 11.5 },
  { name: '慢充桩D', power: true, isCharging: false, isFault: true, count: 8, duration: 3.2, energy: 9.1 },
  { name: '慢充桩E', power: true, isCharging: false, isFault: false, count: 9, duration: 4.5, energy: 10.5 }
])

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

// 切换开关后的行为（如模拟取消充电）
function handlePowerToggle(row) {
  if (!row.power) {
    // 电源关闭后必须停止充电
    row.isCharging = false
  }
  // 不改变 isFault，由外部监控控制
}
</script>
