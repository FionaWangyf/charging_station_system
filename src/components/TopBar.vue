<template>
  <div class="topbar">
    <div class="title">智能充电桩管理系统</div>
    <div class="admin">
      <el-icon class="avatar">
        <User />
      </el-icon>
      <span class="name">Admin</span>
    </div>
  </div>
</template>

<script setup>
import { User } from '@element-plus/icons-vue'
</script>

<style scoped>
.topbar {
  height: 60px;
  background-color: #1E6BFF;
  color: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
.title {
  font-size: 20px;
  font-weight: bold;
}
.admin {
  display: flex;
  align-items: center;
}
.avatar {
  font-size: 28px;
  margin-right: 8px;
}
.name {
  font-size: 14px;
}
</style>
