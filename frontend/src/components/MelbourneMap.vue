<template>
  <div class="melbourne-map">
    <div class="map-header">
      <h1>Melbourne City 停车场地图</h1>
      <p>点击地图区域查看停车场信息，支持缩放操作</p>
    </div>

    <div class="map-container">
      <l-map
        v-model:zoom="zoom"
        :center="center"
        :options="mapOptions"
        class="map"
        @click="onMapClick"
      >
        <l-tile-layer
          :url="tileUrl"
          :attribution="attribution"
        />

        <!-- 停车场标记 -->
        <l-marker
          v-for="parking in parkingLots"
          :key="parking.id"
          :lat-lng="parking.coordinates"
          @click="showParkingInfo(parking)"
        >
          <l-icon
            :icon-size="[32, 32]"
            :icon-anchor="[16, 32]"
            icon-url="/parking-icon.png"
          />
          <l-popup>
            <div class="parking-popup">
              <h3>{{ parking.name }}</h3>
              <p><strong>地址:</strong> {{ parking.address }}</p>
              <p><strong>空位:</strong> {{ parking.available }}/{{ parking.total }}</p>
              <p><strong>价格:</strong> ${{ parking.price }}/小时</p>
              <button @click="navigateToParking(parking)" class="navigate-btn">
                导航至此处
              </button>
            </div>
          </l-popup>
        </l-marker>

        <!-- 区域标记 -->
        <l-circle
          v-for="area in melbourneAreas"
          :key="area.id"
          :lat-lng="area.center"
          :radius="area.radius"
          :color="area.color"
          :fill-color="area.fillColor"
          :fill-opacity="0.3"
          @click="showAreaInfo(area)"
        />
      </l-map>
    </div>

    <!-- 侧边栏信息面板 -->
    <div class="info-panel" v-if="selectedInfo">
      <div class="panel-header">
        <h3>{{ selectedInfo.title }}</h3>
        <button @click="closePanel" class="close-btn">×</button>
      </div>
      <div class="panel-content">
        <div v-if="selectedInfo.type === 'parking'">
          <img :src="selectedInfo.image" alt="停车场图片" class="parking-image">
          <div class="parking-details">
            <p><strong>停车场名称:</strong> {{ selectedInfo.name }}</p>
            <p><strong>详细地址:</strong> {{ selectedInfo.address }}</p>
            <p><strong>开放时间:</strong> {{ selectedInfo.hours }}</p>
            <p><strong>当前状态:</strong>
              <span :class="selectedInfo.available > 10 ? 'status-good' : 'status-limited'">
                {{ selectedInfo.available > 10 ? '空位充足' : '空位有限' }}
              </span>
            </p>
            <div class="availability-bar">
              <div class="bar-fill" :style="{ width: availabilityPercentage + '%' }"></div>
            </div>
            <p class="availability-text">{{ selectedInfo.available }}/{{ selectedInfo.total }} 空位</p>
          </div>
        </div>
        <div v-else-if="selectedInfo.type === 'area'">
          <p><strong>区域描述:</strong> {{ selectedInfo.description }}</p>
          <p><strong>停车场数量:</strong> {{ selectedInfo.parkingCount }}</p>
          <p><strong>平均价格:</strong> ${{ selectedInfo.avgPrice }}/小时</p>
        </div>
      </div>
    </div>

    <!-- 地图控制按钮 -->
    <div class="map-controls">
      <button @click="zoomIn" class="control-btn">+</button>
      <button @click="zoomOut" class="control-btn">-</button>
      <button @click="resetView" class="control-btn">🏠</button>
      <button @click="toggleLayer" class="control-btn">🗺️</button>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { LMap, LTileLayer, LMarker, LPopup, LIcon, LCircle } from '@vue-leaflet/vue-leaflet'
import axios from 'axios'

export default {
  name: 'MelbourneMap',
  components: {
    LMap,
    LTileLayer,
    LMarker,
    LPopup,
    LIcon,
    LCircle
  },
  setup() {
    // 地图配置
    const zoom = ref(13)
    const center = ref([-37.8136, 144.9631]) // Melbourne CBD
    const selectedInfo = ref(null)
    const currentTileLayer = ref('street')

    const mapOptions = {
      zoomSnap: 0.5,
      zoomDelta: 0.5
    }

    // 地图图层
    const tileLayers = {
      street: {
        url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attribution: '© OpenStreetMap contributors'
      },
      satellite: {
        url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        attribution: '© OpenTopoMap contributors'
      }
    }

    const tileUrl = computed(() => tileLayers[currentTileLayer.value].url)
    const attribution = computed(() => tileLayers[currentTileLayer.value].attribution)

    // Melbourne主要区域
    const melbourneAreas = ref([
      {
        id: 1,
        name: 'CBD Central',
        center: [-37.8136, 144.9631],
        radius: 800,
        color: '#3388ff',
        fillColor: '#3388ff',
        description: 'Melbourne市中心商业区，停车位紧张但交通便利',
        parkingCount: 15,
        avgPrice: 8.5
      },
      {
        id: 2,
        name: 'South Melbourne',
        center: [-37.8316, 144.9581],
        radius: 600,
        color: '#ff6b6b',
        fillColor: '#ff6b6b',
        description: '南墨尔本区域，停车相对便宜',
        parkingCount: 8,
        avgPrice: 5.5
      },
      {
        id: 3,
        name: 'East Melbourne',
        center: [-37.8136, 144.9831],
        radius: 500,
        color: '#4ecdc4',
        fillColor: '#4ecdc4',
        description: '东墨尔本，靠近MCG体育场',
        parkingCount: 6,
        avgPrice: 6.0
      }
    ])

    // 停车场数据
    const parkingLots = ref([
      {
        id: 1,
        name: 'Collins Street Parking',
        coordinates: [-37.8136, 144.9631],
        address: '123 Collins Street, Melbourne VIC 3000',
        available: 45,
        total: 200,
        price: 8.5,
        hours: '24小时开放',
        image: '/parking1.jpg'
      },
      {
        id: 2,
        name: 'Flinders Station Parking',
        coordinates: [-37.8183, 144.9671],
        address: 'Flinders Street, Melbourne VIC 3000',
        available: 12,
        total: 150,
        price: 9.0,
        hours: '06:00-22:00',
        image: '/parking2.jpg'
      },
      {
        id: 3,
        name: 'Queen Victoria Market Parking',
        coordinates: [-37.8076, 144.9568],
        address: '65-77 Elizabeth Street, Melbourne VIC 3000',
        available: 89,
        total: 300,
        price: 5.5,
        hours: '07:00-18:00',
        image: '/parking3.jpg'
      },
      {
        id: 4,
        name: 'South Melbourne Parking',
        coordinates: [-37.8316, 144.9581],
        address: '45 Clarendon Street, South Melbourne VIC 3205',
        available: 156,
        total: 180,
        price: 4.0,
        hours: '24小时开放',
        image: '/parking4.jpg'
      },
      {
        id: 5,
        name: 'MCG Sports Parking',
        coordinates: [-37.8200, 144.9834],
        address: 'Brunton Avenue, East Melbourne VIC 3002',
        available: 78,
        total: 500,
        price: 6.0,
        hours: '比赛日开放',
        image: '/parking5.jpg'
      }
    ])

    // 计算停车场可用率
    const availabilityPercentage = computed(() => {
      if (!selectedInfo.value || selectedInfo.value.type !== 'parking') return 0
      return (selectedInfo.value.available / selectedInfo.value.total) * 100
    })

    // 地图事件处理
    const onMapClick = (event) => {
      console.log('地图点击位置:', event.latlng)
      // 可以在这里添加其他点击处理逻辑
    }

    const showParkingInfo = (parking) => {
      selectedInfo.value = {
        type: 'parking',
        title: parking.name,
        ...parking
      }
    }

    const showAreaInfo = (area) => {
      selectedInfo.value = {
        type: 'area',
        title: area.name,
        ...area
      }
    }

    const closePanel = () => {
      selectedInfo.value = null
    }

    const navigateToParking = (parking) => {
      const url = `https://www.google.com/maps/dir/?api=1&destination=${parking.coordinates[0]},${parking.coordinates[1]}`
      window.open(url, '_blank')
    }

    // 地图控制
    const zoomIn = () => {
      zoom.value = Math.min(zoom.value + 1, 18)
    }

    const zoomOut = () => {
      zoom.value = Math.max(zoom.value - 1, 10)
    }

    const resetView = () => {
      center.value = [-37.8136, 144.9631]
      zoom.value = 13
    }

    const toggleLayer = () => {
      currentTileLayer.value = currentTileLayer.value === 'street' ? 'satellite' : 'street'
    }

    // 组件挂载时获取实时停车场数据
    onMounted(async () => {
      try {
        // 从后端API获取停车场数据
        const parkingResponse = await axios.get('/api/parking-lots')
        parkingLots.value = parkingResponse.data

        // 获取Melbourne区域数据
        const areasResponse = await axios.get('/api/melbourne-areas')
        melbourneAreas.value = areasResponse.data

        console.log('Melbourne地图组件已加载，获取到', parkingLots.value.length, '个停车场')
      } catch (error) {
        console.error('获取停车场数据失败:', error)
        // 如果API失败，使用备用数据
        console.log('使用本地备用数据')
      }
    })

    return {
      zoom,
      center,
      mapOptions,
      tileUrl,
      attribution,
      parkingLots,
      melbourneAreas,
      selectedInfo,
      availabilityPercentage,
      onMapClick,
      showParkingInfo,
      showAreaInfo,
      closePanel,
      navigateToParking,
      zoomIn,
      zoomOut,
      resetView,
      toggleLayer
    }
  }
}
</script>

<style scoped>
.melbourne-map {
  height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
}

.map-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1rem 2rem;
  text-align: center;
}

.map-header h1 {
  margin: 0 0 0.5rem 0;
  font-size: 1.8rem;
}

.map-header p {
  margin: 0;
  opacity: 0.9;
}

.map-container {
  flex: 1;
  position: relative;
}

.map {
  height: 100%;
  width: 100%;
}

.parking-popup {
  min-width: 200px;
}

.parking-popup h3 {
  margin: 0 0 0.5rem 0;
  color: #2c3e50;
}

.parking-popup p {
  margin: 0.25rem 0;
  font-size: 0.9rem;
}

.navigate-btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 0.5rem;
  width: 100%;
}

.navigate-btn:hover {
  background: #0056b3;
}

.info-panel {
  position: absolute;
  top: 80px;
  right: 20px;
  width: 350px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 1000;
  max-height: calc(100vh - 140px);
  overflow-y: auto;
}

.panel-header {
  background: #f8f9fa;
  padding: 1rem;
  border-bottom: 1px solid #dee2e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-radius: 8px 8px 0 0;
}

.panel-header h3 {
  margin: 0;
  color: #2c3e50;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6c757d;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #dc3545;
}

.panel-content {
  padding: 1rem;
}

.parking-image {
  width: 100%;
  height: 150px;
  object-fit: cover;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.parking-details p {
  margin: 0.5rem 0;
  font-size: 0.9rem;
}

.status-good {
  color: #28a745;
  font-weight: bold;
}

.status-limited {
  color: #ffc107;
  font-weight: bold;
}

.availability-bar {
  width: 100%;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  margin: 0.5rem 0;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%);
  transition: width 0.3s ease;
}

.availability-text {
  font-size: 0.8rem;
  color: #6c757d;
  text-align: center;
}

.map-controls {
  position: absolute;
  bottom: 20px;
  right: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 1000;
}

.control-btn {
  width: 40px;
  height: 40px;
  background: white;
  border: 2px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1.2rem;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: all 0.2s ease;
}

.control-btn:hover {
  background: #f8f9fa;
  border-color: #007bff;
  transform: translateY(-1px);
}

@media (max-width: 768px) {
  .info-panel {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    top: auto;
    width: auto;
    border-radius: 8px 8px 0 0;
    max-height: 50vh;
  }

  .map-controls {
    bottom: 60px;
    right: 10px;
  }
}
</style>
