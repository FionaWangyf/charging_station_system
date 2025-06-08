<template>
  <div class="app">
    <!-- 登录页面 -->
    <LoginForm
      v-if="currentPage === 'login'"
      @switch-to-register="switchToRegister"
      @login-success="switchToMain"
    />

    <!-- 注册页面 -->
    <RegisterForm
      v-if="currentPage === 'register'"
      @switch-to-login="switchToLogin"
    />

    <!-- 主界面 -->
    <MainPage
      v-if="currentPage === 'main'"
      @switch-to-charging-details="switchToChargingDetails"
    />

    <!-- 充电详单页面 -->
    <ChargingDetailsPage
      v-if="currentPage === 'chargingDetails'"
      @switch-to-main="switchToMain"
    />

  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import LoginForm from './components/LoginPage.vue'
import RegisterForm from './components/RegisterPage.vue'
import MainPage from './components/MainPage.vue'
import ChargingDetailsPage from './components/ChargingDetailsPage.vue'

// 当前页面状态
const currentPage = ref<'login' | 'register' | 'main' | 'chargingDetails'>('login')

// 切换到注册页面
const switchToRegister = () => {
  currentPage.value = 'register'
}

// 切换到登录页面
const switchToLogin = () => {
  currentPage.value = 'login'
}

// 切换到主界面
const switchToMain = () => {
  currentPage.value = 'main'
  console.log('跳转到主界面')
}

// 切换到充电详单页面
const switchToChargingDetails = () => {
  currentPage.value = 'chargingDetails'
  console.log('跳转到充电详单页面')
}
</script>

<style scoped>
.app {
  width: 100%;
  height: 100vh;
}
</style>
