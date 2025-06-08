import { createRouter, createWebHistory } from 'vue-router'
import ChargingPileView from '@/views/ChargingPileView.vue'
import WaitingVehiclesView from '@/views/WaitingVehiclesView.vue'
import ReportView from '@/views/ReportView.vue'

const routes = [
  { path: '/', redirect: '/charging' },
  { path: '/charging', component: ChargingPileView },
  { path: '/waiting', component: WaitingVehiclesView },
  { path: '/report', component: ReportView } 
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
