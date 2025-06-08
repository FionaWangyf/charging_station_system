<template>
  <div class="full">
    <TopBar />
    <div class="container">
      <SidebarMenu />
      <div class="content">
        <h2>报表统计</h2>

        <div class="toolbar">
          <el-radio-group v-model="rangeType" size="small">
            <el-radio-button value="日">日</el-radio-button>
            <el-radio-button value="周">周</el-radio-button>
            <el-radio-button value="月">月</el-radio-button>
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
import { ElMessage } from 'element-plus'
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

 // 添加调试输出
    console.log('🔍 API响应:', response)
    console.log('🔍 响应类型:', typeof response)
    console.log('🔍 响应数据:', response?.data)

    // 检查响应数据
    console.log('🔍 完整响应:', response)

    // 尝试不同的数据访问方式
    let data = response
    if (response?.data) {
      data = response.data
    }
    if (Array.isArray(data)) {
      report.value = data.map(item => ({
        id: item.pile_id || 'Unknown',
        count: item.charging_count || 0,
        time: Number(item.power_consumed || 0).toFixed(1), // 暂时用功率代替时长
        kwh: Number(item.power_consumed || 0).toFixed(1),
        chargeFee: Number(item.revenue || 0).toFixed(2),
        serviceFee: (Number(item.revenue || 0) * 0.2).toFixed(2),
        totalFee: Number(item.revenue || 0).toFixed(2)
      }))
      
      console.log('🔍 处理后的报表数据:', report.value)
    } else {
      console.log('❌ 数据不是数组:', data)
      report.value = []
      ElMessage.warning('数据格式错误')
    }
/*
    // 检查响应数据
    if (response && response.data) {
      // 转换数据格式
      report.value = response.data.map(item => ({
        id: item.pile_id || 'Unknown',
        count: item.charging_count || 0,
        time: (Number(item.power_consumed || 0) / 30).toFixed(1), // 假设平均功率30kW来估算时长
        kwh: Number(item.power_consumed || 0).toFixed(1),
        chargeFee: (Number(item.revenue || 0) * 0.8).toFixed(2), // 充电费为总费用的80%
        serviceFee: (Number(item.revenue || 0) * 0.2).toFixed(2), // 估算服务费
        totalFee: Number(item.revenue || 0).toFixed(2)
      }))
    } else {
      report.value = []
      ElMessage.warning('暂无统计数据')
    }
  */
  } catch (error) {
    console.error('获取统计数据失败:', error)
    ElMessage.error('获取统计数据失败')
    report.value = []
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
  height: 100vh;
}
.container {
  display: flex;
  flex: 1;
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