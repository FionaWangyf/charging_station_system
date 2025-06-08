<template>
  <div class="full">
    <TopBar />
    <div class="container">
      <SidebarMenu />
      <div class="content">
        <h2>充电桩列表</h2>
        <div class="table-wrapper">
          <ChargingPileTable />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import TopBar from '@/components/TopBar.vue'
import SidebarMenu from '@/components/SidebarMenu.vue'
import ChargingPileTable from '@/components/ChargingPileTable.vue'
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
  padding-left: 25px;
  padding-top: 10px;
  background-color: #fff;
}
.table-wrapper {
  margin-left: 40px;
  margin-top: 40px;
  width: 95%;
}
</style>
