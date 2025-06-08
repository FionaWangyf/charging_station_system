<template>
  <el-card shadow="always" class="pile-card">
    <div class="header">
      <h3>{{ pileName }}</h3>
      <span class="count">等候车辆数：{{ queue.length }}</span>
    </div>
    <div class="vehicle" v-for="(car, index) in queue" :key="index">
      <div class="info-row"><span class="label">用户 ID：</span>{{ car.userId }}</div>
      <div class="info-row"><span class="label">电池容量：</span>{{ car.capacity }} 度</div>
      <div class="info-row"><span class="label">请求电量：</span>{{ car.request }} 度</div>
      <div class="info-row"><span class="label">排队时长：</span>{{ car.waitingTime }} h</div>
      <el-divider v-if="index < queue.length - 1" />
    </div>
    <div v-if="queue.length === 0" class="empty">
      当前无等候车辆
    </div>
  </el-card>
</template>

<script setup>


defineProps({
  pileName: String,
  queue: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.pile-card {
  padding: 16px;
  border-radius: 12px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.count {
  font-size: 14px;
  color: #999;
}
.info-row {
  margin: 6px 0;
  font-size: 14px;
}
.label {
  font-weight: 500;
  color: #409EFF;
}
.empty {
  color: #ccc;
  font-style: italic;
  text-align: center;
  margin-top: 10px;
}
</style>
