import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import MelbourneParkingMap from './components/MelbourneParkingMap.vue'

const routes = [
  { path: '/', component: MelbourneParkingMap },
  { path: '/map', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

createApp(App).use(router).mount('#app')
