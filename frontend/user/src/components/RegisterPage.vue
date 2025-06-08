<template>
  <div class="login-container">
    <div class="background-overlay"></div>

    <div class="login-content">
      <h1 class="title">用户注册</h1>

      <div class="login-form">
        <div class="form-group">
          <input
            v-model="registerForm.username"
            type="text"
            placeholder="请输入账号"
            class="form-input"
            :disabled="loading"
          />
        </div>

        <div class="form-group">
          <input
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码"
            class="form-input"
            :disabled="loading"
          />
        </div>

        <div class="form-group">
          <input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="再次输入密码"
            class="form-input"
            :disabled="loading"
            @keyup.enter="handleRegister"
          />
        </div>

        <div class="form-group">
          <input
            v-model="registerForm.carId"
            type="text"
            placeholder="请输入车牌号（如：京A12345）"
            class="form-input"
            :disabled="loading"
            maxlength="8"
          />
        </div>

        <div class="form-group">
          <input
            v-model="registerForm.carCapacity"
            type="number"
            placeholder="请输入电池容量（kWh）"
            class="form-input"
            :disabled="loading"
            min="20"
            max="200"
          />
        </div>

        <!-- 错误提示 -->
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <!-- 成功提示 -->
        <div v-if="successMessage" class="success-message">
          {{ successMessage }}
        </div>

        <button @click="handleRegister" class="login-button" :disabled="loading">
          <span v-if="loading">注册中...</span>
          <span v-else>注 册</span>
        </button>

        <div class="register-link">
          <a href="#" class="link" @click.prevent="$emit('switchToLogin')">已有账号？立即登录</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onUnmounted } from 'vue'

// 定义事件
defineEmits<{
  switchToLogin: []
}>()

interface RegisterForm {
  username: string
  password: string
  confirmPassword: string
  carId: string        // 新增
  carCapacity: number  // 新增
}

const registerForm = reactive<RegisterForm>({
  carId: '', 
  username: '',
  password: '',
  confirmPassword: '',
  carCapacity: 60 
})

const loading = ref<boolean>(false)
const errorMessage = ref<string>('')
const successMessage = ref<string>('')

// 清除消息的定时器
let errorTimer: number | null = null
let successTimer: number | null = null

const showError = (message: string) => {
  errorMessage.value = message
  successMessage.value = ''

  // 如果已有定时器，先清除
  if (errorTimer) {
    clearTimeout(errorTimer)
  }

  // 3秒后清除错误消息
  errorTimer = setTimeout(() => {
    errorMessage.value = ''
  }, 1000)
}

const showSuccess = (message: string) => {
  successMessage.value = message
  errorMessage.value = ''

  // 如果已有定时器，先清除
  if (successTimer) {
    clearTimeout(successTimer)
  }

  // 3秒后清除成功消息
  successTimer = setTimeout(() => {
    successMessage.value = ''
  }, 1000)
}

// 验证注册表单
const validateForm = (): boolean => {
  if (!registerForm.username) {
    showError('请输入账号')
    return false
  }

  if (!registerForm.password) {
    showError('请输入密码')
    return false
  }

  if (!registerForm.confirmPassword) {
    showError('请再次输入密码')
    return false
  }

  if (registerForm.password !== registerForm.confirmPassword) {
    showError('两次输入的密码不一致')
    return false
  }

  if (!registerForm.carId) {
    showError('请输入车牌号')
    return false
  }

  // 简单的车牌号格式验证
  const carIdPattern = /^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5}$/
  if (!carIdPattern.test(registerForm.carId)) {
    showError('请输入正确的车牌号格式')
    return false
  }

  if (!registerForm.carCapacity || registerForm.carCapacity < 20 || registerForm.carCapacity > 200) {
    showError('请输入有效的电池容量（20-200kWh）')
    return false
  }

  return true
}

const handleRegister = async (): Promise<void> => {
  // 清除之前的消息
  errorMessage.value = ''
  successMessage.value = ''

  // 验证表单
  if (!validateForm()) {
    return
  }

  loading.value = true

  try {
    // 调用后端注册API
    const response = await fetch('/api/user/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      credentials: 'include',
      body: JSON.stringify({
        car_id:registerForm.carId, 
        username: registerForm.username,
        password: registerForm.password,
        car_capacity: registerForm.carCapacity // 默认电池容量
      })
    })

    const result = await response.json()

    // 根据HTTP状态码和响应内容判断注册结果
    if (response.ok && (result.success === true || result.code === 200)) {
      // 注册成功
      console.log('注册成功:', result)

      showSuccess('注册成功！3秒后跳转到登录页面...')

      // 清空表单
      registerForm.username = ''
      registerForm.password = ''
      registerForm.confirmPassword = ''

      // 3秒后跳转到登录页面
      setTimeout(() => {
        emit('switchToLogin')
      }, 3000)

    } else {
      // 注册失败 - 显示服务器返回的具体错误消息
      const errorMsg = result.message || result.msg || '注册失败，请稍后重试'
      showError(errorMsg)
    }

  } catch (error) {
    console.error('注册请求失败:', error)

    // 网络错误或JSON解析错误
    if (error instanceof TypeError && error.message.includes('fetch')) {
      showError('网络连接失败，请检查网络连接')
    } else {
      showError('服务器响应异常，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

// 组件卸载时清理定时器
onUnmounted(() => {
  if (errorTimer) {
    clearTimeout(errorTimer)
  }
  if (successTimer) {
    clearTimeout(successTimer)
  }
})
</script>

<style scoped>
.login-container {
  position: relative;
  width: 100%;
  height: 100vh;
  background-image: url('/LoginBackground.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  display: flex;
  justify-content: center;
  align-items: center;
}

.background-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
}

.login-content {
  position: relative;
  z-index: 2;
  text-align: center;
}

.title {
  color: white;
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 30px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

.login-form {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 40px;
  width: 400px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.form-group {
  margin-bottom: 20px;
}

.form-input {
  width: 100%;
  height: 50px;
  border: none;
  border-radius: 25px;
  background: rgba(255, 255, 255, 0.3);
  padding: 0 20px;
  font-size: 16px;
  outline: none;
  transition: all 0.3s ease;
}

.form-input:focus {
  background: rgba(255, 255, 255, 1);
  box-shadow: 0 0 10px rgba(0, 188, 212, 0.3);
}

.form-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-input::placeholder {
  color: #ffffff;
}

.error-message {
  background: rgba(244, 67, 54, 0.9);
  color: white;
  padding: 12px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
  animation: slideIn 0.3s ease-out;
}

.success-message {
  background: rgba(76, 175, 80, 0.9);
  color: white;
  padding: 12px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-button {
  width: 200px;
  height: 50px;
  border: none;
  border-radius: 25px;
  background: linear-gradient(135deg, #00bcd4, #00acc1);
  color: white;
  font-size: 18px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  margin: 30px 0 15px 0;
}

.login-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #00acc1, #0097a7);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 188, 212, 0.4);
}

.login-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.register-link {
  text-align: center;
  margin-top: 15px;
}

.link {
  color: #ffffff;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.3s ease;
}

.link:hover {
  color: #00bcd4;
}

/* 响应式设计 */
@media (max-width: 480px) {
  .login-form {
    width: 90%;
    padding: 30px 20px;
  }

  .title {
    font-size: 24px;
    margin-bottom: 30px;
  }
}
</style>
