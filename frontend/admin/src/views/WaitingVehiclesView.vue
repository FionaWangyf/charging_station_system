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
import TopBar from '@/components/TopBar.vue'
import SidebarMenu from '@/components/SidebarMenu.vue'
import WaitingPileCard from '@/components/WaitingPileCard.vue'

const piles = [
  {
    name: '快充桩 A',
    queue: [
      { userId: '12345', capacity: 40, request: 30, waitingTime: 30 },
    ]
  },
  {
    name: '快充桩 B',
    queue: [
      { userId: '12345', capacity: 40, request: 30, waitingTime: 30 },
      { userId: '12345', capacity: 40, request: 30, waitingTime: 30 },
    ]
  },
  {
    name: '慢充桩 C',
    queue: [
      { userId: '12345', capacity: 40, request: 30, waitingTime: 30 }
    ]
  },
  {
    name: '慢充桩 D',
    queue: [
      { userId: '12345', capacity: 40, request: 30, waitingTime: 30 }
    ]
  },
  {
    name: '慢充桩 E',
    queue: []
  }
]
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
