<template>
  <div class="full">
    <TopBar />
    <div class="container">
      <SidebarMenu />
      <div class="content">
        <h2>报表统计</h2>

        <div class="toolbar">
          <el-radio-group v-model="rangeType" size="small">
            <el-radio-button label="日" />
            <el-radio-button label="周" />
            <el-radio-button label="月" />
          </el-radio-group>

          <el-date-picker
            v-model="date"
            :type="pickerType"
            :format="dateFormat"
            :value-format="valueFormat"
            placeholder="选择日期"
            size="small"
            style="margin-left: 12px;"
          />
        </div>

        <ReportTable :report="report" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '@/api'
import TopBar from '@/components/TopBar.vue'
import SidebarMenu from '@/components/SidebarMenu.vue'
import ReportTable from '@/components/ReportTable.vue'

const report = ref([])
const loading = ref(false)

// 报表类型：日、周、月
const rangeType = ref('日')

// 日期值
const date = ref(new Date())

// 根据报表类型动态切换 picker 类型
const pickerType = computed(() => {
  switch (rangeType.value) {
    case '日': return 'date'
    case '周': return 'week'
    case '月': return 'month'
    default: return 'date'
  }
})

// 动态格式化显示格式（用户界面上的）
const dateFormat = computed(() => {
  switch (rangeType.value) {
    case '日': return 'YYYY/MM/DD'
    case '周': return 'gggg [第] ww [周]'  // 显示为：2025 第 23 周
    case '月': return 'YYYY/MM'
    default: return 'YYYY/MM/DD'
  }
})

// 动态格式化值格式（用于绑定、传参）
const valueFormat = computed(() => {
  switch (rangeType.value) {
    case '日': return 'YYYY-MM-DD'
    case '周': return 'gggg-[W]WW'
    case '月': return 'YYYY-MM'
    default: return 'YYYY-MM-DD'
  }
})

// 获取统计数据
async function fetchStatistics() {
  loading.value = true
  try {
    let response
    switch (rangeType.value) {
      case '日':
        response = await api.statistics.getDaily(1)
        break
      case '周':
        response = await api.statistics.getDaily(7)
        break
      case '月':
        response = await api.statistics.getDaily(30)
        break
    }

// 转换数据格式
    report.value = response.data.map(item => ({
      id: item.pile_id || 'Unknown',
      count: item.charging_count || 0,
      time: Number(item.power_consumed || 0).toFixed(1),
      kwh: Number(item.power_consumed || 0).toFixed(1),
      chargeFee: Number(item.revenue || 0).toFixed(2),
      serviceFee: (Number(item.revenue || 0) * 0.2).toFixed(2), // 估算服务费
      totalFee: Number(item.revenue || 0).toFixed(2)
    }))
  } catch (error) {
    ElMessage.error('获取统计数据失败')
  } finally {
    loading.value = false
  }
}
// 监听报表类型和日期变化
watch([rangeType, date], () => {
  fetchStatistics()
})

onMounted(() => {
  fetchStatistics()
})
</script>

<style scoped>
.full {
  display: flex;
  flex-direction: column;
  height: 200vh;
}
.container {
  display: flex;
}
.content {
  flex: 1;
  padding: 24px;
  background-color: #fff;
  width: 100%;
}
.toolbar {
  margin-bottom: 26px;
  display: flex;
  align-items: center;
}
</style>
