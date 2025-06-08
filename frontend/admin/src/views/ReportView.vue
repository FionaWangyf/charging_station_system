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
import { ref, computed } from 'vue'
import TopBar from '@/components/TopBar.vue'
import SidebarMenu from '@/components/SidebarMenu.vue'
import ReportTable from '@/components/ReportTable.vue'

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

// 示例数据
const report = ref([
  { id: 'FA', count: 15, time: 65, kwh: 122, chargeFee: 245, serviceFee: 18, totalFee: 263 },
  { id: 'FB', count: 12, time: 52, kwh: 110, chargeFee: 220, serviceFee: 16, totalFee: 236 },
  { id: 'TC', count: 20, time: 78, kwh: 140, chargeFee: 280, serviceFee: 21, totalFee: 301 },
  { id: 'TD', count: 18, time: 72, kwh: 130, chargeFee: 260, serviceFee: 19, totalFee: 279 },
  { id: 'TE', count: 10, time: 40, kwh: 100, chargeFee: 200, serviceFee: 15, totalFee: 215 }
])
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
