<template>
  <div class="login-container">
    <div class="background-overlay"></div>

    <div class="login-content">
      <h1 class="title">智能充电桩系统平台</h1>

      <div class="login-form">
        <div class="form-group">
          <input
            v-model="loginForm.username"
            type="text"
            placeholder="请输入账号"
            class="form-input"
            :disabled="loading"
          />
        </div>

        <div class="form-group">
          <input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            class="form-input"
            :disabled="loading"
            @keyup.enter="handleLogin"
          />
        </div>

        <!-- 错误提示 -->
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <button @click="handleLogin" class="login-button" :disabled="loading">
          <span v-if="loading">登录中...</span>
          <span v-else>登 录</span>
        </button>

        <div class="form-links">
          <a href="#" class="link" @click.prevent="emit('switchToRegister')">注册</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref} from 'vue'

const emit = defineEmits<{
  switchToRegister: []
  loginSuccess: []     // 新增：登录成功事件
}>()


interface LoginForm {
  username: string
  password: string
}

const loginForm = reactive<LoginForm>({
  username: '',
  password: ''
})

const loading = ref<boolean>(false)
const errorMessage = ref<string>('')

// 清除错误消息的定时器
let errorTimer: number | null = null

const showError = (message: string) => {
  errorMessage.value = message

  // 如果已有定时器，先清除
  if (errorTimer) {
    clearTimeout(errorTimer)
  }

  // 1秒后清除错误消息
  errorTimer = setTimeout(() => {
    errorMessage.value = ''
  }, 1000)
}

const handleLogin = async (): Promise<void> => {
  // 清除之前的错误消息
  errorMessage.value = ''

  if (!loginForm.username || !loginForm.password) {
    showError('请输入账号和密码')
    return
  }

  loading.value = true

  
  try {

    // 请根据你的实际后端接口地址修改URL
    const response =await fetch('/api/user/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      credentials: 'include', // 重要：包含cookies
      body: JSON.stringify({
        username: loginForm.username,
        password: loginForm.password
      })
    })
    console.log('📡 请求已发送，等待响应...')
    console.log('📥 响应对象:', response)
    const result = await response.json()

    // 根据HTTP状态码和响应内容判断登录结果
    if (response.ok && (result.success === true || result.code === 200)) {
      // 登录成功
      console.log('登录成功:', result)

      // 存储用户信息
      if (result.data?.user_info) {
        localStorage.setItem('userInfo', JSON.stringify(result.data.user_info))
      }

      // 发出登录成功事件，跳转到主界面
      emit('loginSuccess')

      } else {
      // 登录失败 - 显示服务器返回的具体错误消息
      const errorMsg = result.message || result.msg || '用户名或密码错误'
      showError(errorMsg)
    }

  } catch (error) {
    console.error('登录请求失败:', error)

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

.form-input::placeholder {
  color: #ffffff;
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
  margin: 30px 0 20px 0;
}

.login-button:hover {
  background: linear-gradient(135deg, #00acc1, #0097a7);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 188, 212, 0.4);
}

.form-links {
  display: flex;
  justify-content: right;
  margin-top: 20px;
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

.error-message {
  background: rgba(244, 67, 54, 0.9);
  color: white;
  padding: 12px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
  animation: slideIn 0.3s ease-out;
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
