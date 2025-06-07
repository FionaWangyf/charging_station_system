<template>
  <el-menu
    :default-active="$route.path"
    class="el-menu-vertical-demo"
    background-color="#1E6BFF"
    text-color="#fff"
    active-text-color="#ffd04b"
    router
  >
    <el-menu-item index="/charging">
      <el-icon><i class="el-icon-battery" /></el-icon>
      <router-link to="/charging">充电桩管理</router-link>
    </el-menu-item>

    <el-menu-item index="/waiting">
      <el-icon><i class="el-icon-truck" /></el-icon>
      <router-link to="/waiting">等候车辆</router-link>
    </el-menu-item>

    <el-menu-item index="/report">
      <el-icon><i class="el-icon-data-analysis" /></el-icon>
      <router-link to="/report">报表统计</router-link>
    </el-menu-item>
  </el-menu>
</template>

<script setup>
import { useRoute } from 'vue-router'
</script>

<style scoped>
.el-menu {
  height: 120vh;
  width: 220px;
}
a {
  color: inherit;
  text-decoration: none;
  font-size: 16px;
  margin-left: 0;
}
</style>
