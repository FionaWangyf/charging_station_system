<template>
  <div class="full">
    <TopBar />
    <div class="container">
      <SidebarMenu />
      <div class="content">
        <h2>等候车辆</h2>
        <div class="grid">
          <WaitingPileCard
            v-for="pile in piles"
            :key="pile.name"
            :pileName="pile.name"
            :queue="pile.queue"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '@/api'

import TopBar from '@/components/TopBar.vue'
import SidebarMenu from '@/components/SidebarMenu.vue'
import WaitingPileCard from '@/components/WaitingPileCard.vue'

const piles = ref([])
const loading = ref(false)


async function fetchQueueInfo() {
  loading.value = true
  try {
    const response = await api.admin.getQueueInfo()
    const queueData = response.data.queue_info
    
    // 转换数据格式
    piles.value = [
      {
        name: '快充桩 A',
        queue: queueData.charging_sessions.filter(s => s.pile_id === 'A').map(mapSessionToQueue)
      },
      {
        name: '快充桩 B', 
        queue: queueData.charging_sessions.filter(s => s.pile_id === 'B').map(mapSessionToQueue)
      },
      {
        name: '慢充桩 C', 
        queue: queueData.charging_sessions.filter(s => s.pile_id === 'C').map(mapSessionToQueue)
      },
      {
        name: '慢充桩 D', 
        queue: queueData.charging_sessions.filter(s => s.pile_id === 'D').map(mapSessionToQueue)
      },
      // ... 其他充电桩
      {
        name: '慢充桩 E', 
        queue: queueData.charging_sessions.filter(s => s.pile_id === 'E').map(mapSessionToQueue)
      },
    ]
  } catch (error) {
    ElMessage.error('获取队列信息失败')
  } finally {
    loading.value = false
  }
}

function mapSessionToQueue(session) {
  return {
    userId: session.user_id,
    capacity: session.requested_amount,
    request: session.actual_amount || 0,
    waitingTime: calculateWaitingTime(session.created_at)
  }
}

onMounted(() => {
  fetchQueueInfo()
  setInterval(fetchQueueInfo, 3000)
})

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
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}
</style>
