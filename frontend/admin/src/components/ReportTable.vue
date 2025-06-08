<template>

    <!-- 你现有的列定义 -->
  <el-table :data="report" border stripe style="width: 100%">
    <el-table-column prop="id" label="充电桩编号" width="180" />
    <el-table-column prop="count" label="累计充电次数" width="200" />
    <el-table-column prop="time" label="累计充电时长（h）" width="220" />
    <el-table-column prop="kwh" label="累计充电量（kWh）" width="220" />
    <el-table-column prop="chargeFee" label="累计充电费用（元）" width="220" />
    <el-table-column prop="serviceFee" label="累计服务费用（元）" width="220" />
    <el-table-column prop="totalFee" label="累计总费用（元）" width="220" />
    <el-table-column prop="others" label="备注" width="125" />
  </el-table>
</template>

<script setup>
defineProps({
  report: {
    type: Array,
    default: () => []
  }
})
</script>
