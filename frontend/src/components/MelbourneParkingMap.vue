<template>
  <div class="parking-app">
    <!-- Top navigation bar -->
    <div class="top-nav">
      <div class="nav-left">
        <button class="menu-btn" @click="toggleMenu">☰</button>
        <h1 class="app-title">Melbourne Parking</h1>
      </div>
      <div class="nav-right">
        <button class="user-location-btn" @click="centerOnUser" title="Find my location">
          📍
        </button>
      </div>
    </div>

    <!-- Search bar -->
    <div class="search-container">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input
          type="text"
          v-model="searchQuery"
          @input="onSearch"
          placeholder="Search address or parking lot..."
          class="search-input"
        />
        <button v-if="searchQuery" @click="clearSearch" class="clear-btn">×</button>
      </div>
    </div>

    <!-- Map container -->
    <div class="map-container">
      <div id="map" class="map-element"></div>
    </div>

    <!-- Parking information panel -->
    <div class="info-panel" v-if="selectedParking" :class="{ 'mobile-panel': isMobile }">
      <div class="panel-header">
        <h3>{{ selectedParking.name }}</h3>
        <button @click="closePanel" class="close-btn">×</button>
      </div>
      <div class="panel-content">
        <p><strong>Address:</strong> {{ selectedParking.address }}</p>
        <p><strong>Available Spaces:</strong> {{ selectedParking.available }}/{{ selectedParking.total }}</p>
        <p><strong>Price:</strong> ${{ selectedParking.price }}/hour</p>
        <p><strong>Operating Hours:</strong> {{ selectedParking.hours }}</p>
        <p><strong>Area:</strong> {{ selectedParking.area }}</p>
        <div class="availability-indicator">
          <div class="availability-bar">
            <div class="bar-fill" :style="{ width: availabilityPercentage + '%' }"></div>
          </div>
          <span class="availability-text">{{ Math.round(availabilityPercentage) }}% available</span>
        </div>
        <div class="facilities" v-if="selectedParking.facilities && selectedParking.facilities.length">
          <h4>Facilities:</h4>
          <div class="facility-tags">
            <span v-for="facility in selectedParking.facilities" :key="facility" class="facility-tag">
              {{ facility }}
            </span>
          </div>
        </div>
        <div class="action-buttons">
          <button @click="startParking" class="action-btn primary">Start Parking</button>
          <button @click="getDirections" class="action-btn secondary">Get Directions</button>
        </div>
      </div>
    </div>

    <!-- Loading indicator -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <p>Loading parking data...</p>
    </div>

    <!-- Error message -->
    <div v-if="errorMessage" class="error-message">
      <p>{{ errorMessage }}</p>
      <button @click="dismissError" class="dismiss-btn">Dismiss</button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, nextTick, onUnmounted } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import 'leaflet.markercluster'
import axios from 'axios'

export default {
  name: 'ParkingMap',
  setup() {
    const searchQuery = ref('')
    const selectedParking = ref(null)
    const loading = ref(true)
    const currentLayer = ref('street')
    const mapContainer = ref(null)
    let map = null
    let markerClusterGroup = null
    let userMarker = null
    let updateInterval = null

    // 停车场数据
    const parkingLots = ref([])
    const userLocation = ref(null)

    // 计算属性
    const nearbyParkingCount = computed(() => parkingLots.value.length)
    const availableSpaces = computed(() =>
      parkingLots.value.reduce((sum, parking) => sum + parking.available, 0)
    )

    // API基础URL
    const API_BASE = '/api'

    // 初始化地图
    const initMap = async () => {
      await nextTick()

      // 创建地图
      map = L.map('map').setView([-37.8136, 144.9631], 13)

      // 添加图层
      const streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      })

      const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles © Esri'
      })

      streetLayer.addTo(map)

      // 创建标记聚类组
      markerClusterGroup = L.markerClusterGroup({
        iconCreateFunction: function(cluster) {
          const childCount = cluster.getChildCount()
          return L.divIcon({
            html: '<div><span>' + childCount + '</span></div>',
            className: 'marker-cluster custom-cluster',
            iconSize: L.point(40, 40)
          })
        }
      })

      map.addLayer(markerClusterGroup)

      // 获取用户位置
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            userLocation.value = [position.coords.latitude, position.coords.longitude]
            addUserMarker()
            // 获取附近停车场
            loadNearbyParkingData()
          },
          (error) => {
            console.log('无法获取位置:', error)
            // 使用默认位置
            loadParkingData()
          }
        )
      } else {
        loadParkingData()
      }

      // 开始定期更新数据
      startRealTimeUpdates()
    }

    // 加载停车场数据
    const loadParkingData = async () => {
      try {
        loading.value = true
        const response = await axios.get(`${API_BASE}/parking-lots`)

        if (response.data.success) {
          parkingLots.value = response.data.data.map(lot => ({
            ...lot,
            coordinates: lot.coordinates,
            distance: calculateDistance(lot.coordinates) // 计算距离
          }))
          updateParkingMarkers()
        }
      } catch (error) {
        console.error('加载停车场数据失败:', error)
        // 使用备用数据
        loadFallbackData()
      } finally {
        loading.value = false
      }
    }

    // 加载附近停车场数据
    const loadNearbyParkingData = async () => {
      if (!userLocation.value) return

      try {
        loading.value = true
        const [lat, lng] = userLocation.value
        const response = await axios.get(`${API_BASE}/parking-lots/nearby`, {
          params: { lat, lng, radius: 2000 }
        })

        if (response.data.success) {
          parkingLots.value = response.data.data
          updateParkingMarkers()
        }
      } catch (error) {
        console.error('加载附近停车场数据失败:', error)
        loadParkingData() // 回退到加载所有数据
      } finally {
        loading.value = false
      }
    }

    // 备用数据（当API不可用时）
    const loadFallbackData = () => {
      const mockData = [
        {
          id: 1,
          name: 'Collins Street Car Park',
          coordinates: [-37.8136, 144.9631],
          available: 45,
          total: 200,
          price: 8.50,
          distance: 120,
          hours: '24小时',
          area: 'CBD',
          facilities: ['电动车充电', '安全监控', '残疾人车位']
        },
        {
          id: 2,
          name: 'Flinders Street Station Parking',
          coordinates: [-37.8183, 144.9671],
          available: 23,
          total: 150,
          price: 6.00,
          distance: 280,
          hours: '6:00-22:00',
          area: 'CBD',
          facilities: ['公共交通接驳', '安全监控']
        },
        {
          id: 3,
          name: 'Southern Cross Parking',
          coordinates: [-37.8184, 144.9525],
          available: 67,
          total: 300,
          price: 7.20,
          distance: 450,
          hours: '24小时',
          area: 'Docklands',
          facilities: ['电动车充电', '洗车服务', '安全监控']
        },
        {
          id: 4,
          name: 'Queen Victoria Market Parking',
          coordinates: [-37.8076, 144.9568],
          available: 89,
          total: 400,
          price: 5.50,
          distance: 650,
          hours: '6:00-18:00',
          area: 'North Melbourne',
          facilities: ['购物便利', '安全监控']
        },
        {
          id: 5,
          name: 'Federation Square Parking',
          coordinates: [-37.8179, 144.9690],
          available: 12,
          total: 180,
          price: 9.00,
          distance: 180,
          hours: '24小时',
          area: 'CBD',
          facilities: ['文化景点', '餐饮便利', '安全监控']
        }
      ]

      parkingLots.value = mockData
      updateParkingMarkers()
    }

    // 计算距离
    const calculateDistance = (coordinates) => {
      if (!userLocation.value) return 0

      const [lat1, lng1] = userLocation.value
      const [lat2, lng2] = coordinates

      const R = 6371e3 // 地球半径（米）
      const φ1 = lat1 * Math.PI/180
      const φ2 = lat2 * Math.PI/180
      const Δφ = (lat2-lat1) * Math.PI/180
      const Δλ = (lng2-lng1) * Math.PI/180

      const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
                Math.cos(φ1) * Math.cos(φ2) *
                Math.sin(Δλ/2) * Math.sin(Δλ/2)
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))

      return Math.round(R * c)
    }

    // 更新停车场标记
    const updateParkingMarkers = () => {
      if (!markerClusterGroup) return

      // 清除现有标记
      markerClusterGroup.clearLayers()

      parkingLots.value.forEach(parking => {
        const availability = parking.available / parking.total
        let iconColor = '#ff4444' // 红色 - 很少
        let statusText = '车位紧张'

        if (availability > 0.5) {
          iconColor = '#44ff44' // 绿色 - 充足
          statusText = '车位充足'
        } else if (availability > 0.2) {
          iconColor = '#ffaa44' // 橙色 - 中等
          statusText = '车位一般'
        }

        const icon = L.divIcon({
          html: `
            <div class="parking-marker" style="background-color: ${iconColor}" title="${statusText}">
              <span class="parking-count">${parking.available}</span>
            </div>
          `,
          className: 'custom-parking-marker',
          iconSize: [30, 30],
          iconAnchor: [15, 15]
        })

        const marker = L.marker(parking.coordinates, { icon })
          .on('click', () => selectParking(parking))

        markerClusterGroup.addLayer(marker)
      })
    }

    // 添加用户位置标记
    const addUserMarker = () => {
      if (userLocation.value && map) {
        const userIcon = L.divIcon({
          html: '<div class="user-marker">📍</div>',
          className: 'user-location-marker',
          iconSize: [20, 20],
          iconAnchor: [10, 10]
        })

        if (userMarker) {
          map.removeLayer(userMarker)
        }

        userMarker = L.marker(userLocation.value, { icon: userIcon }).addTo(map)
      }
    }

    // 开始实时更新
    const startRealTimeUpdates = () => {
      // 每30秒更新一次数据
      updateInterval = setInterval(() => {
        if (userLocation.value) {
          loadNearbyParkingData()
        } else {
          loadParkingData()
        }
      }, 30000)
    }

    // 停止实时更新
    const stopRealTimeUpdates = () => {
      if (updateInterval) {
        clearInterval(updateInterval)
        updateInterval = null
      }
    }

    // 选择停车场
    const selectParking = async (parking) => {
      selectedParking.value = parking
      map.setView(parking.coordinates, 16)

      // 尝试获取详细信息
      try {
        const response = await axios.get(`${API_BASE}/parking-lots/${parking.id}`)
        if (response.data.success) {
          selectedParking.value = { ...parking, ...response.data.data }
        }
      } catch (error) {
        console.log('获取详细信息失败:', error)
      }
    }

    // 关闭详情
    const closeDetails = () => {
      selectedParking.value = null
    }

    // 定位到用户位置
    const centerOnUser = () => {
      if (userLocation.value && map) {
        map.setView(userLocation.value, 15)
      } else {
        // 请求获取位置
        if (navigator.geolocation) {
          navigator.geolocation.getCurrentPosition(
            (position) => {
              userLocation.value = [position.coords.latitude, position.coords.longitude]
              addUserMarker()
              map.setView(userLocation.value, 15)
              loadNearbyParkingData()
            },
            (error) => {
              alert('无法获取您的位置，请检查位置权限设置')
            }
          )
        }
      }
    }

    // 搜索功能
    const onSearch = async () => {
      if (!searchQuery.value.trim()) return

      try {
        loading.value = true
        const response = await axios.get(`${API_BASE}/parking-lots/search`, {
          params: { q: searchQuery.value }
        })

        if (response.data.success) {
          parkingLots.value = response.data.data.map(lot => ({
            ...lot,
            distance: calculateDistance(lot.coordinates)
          }))
          updateParkingMarkers()

          if (parkingLots.value.length > 0) {
            // 调整地图视图以显示搜索结果
            const bounds = L.latLngBounds(parkingLots.value.map(lot => lot.coordinates))
            map.fitBounds(bounds, { padding: [20, 20] })
          }
        }
      } catch (error) {
        console.error('搜索失败:', error)
      } finally {
        loading.value = false
      }
    }

    const clearSearch = () => {
      searchQuery.value = ''
      if (userLocation.value) {
        loadNearbyParkingData()
      } else {
        loadParkingData()
      }
    }

    // 地图控制
    const zoomIn = () => map && map.zoomIn()
    const zoomOut = () => map && map.zoomOut()

    // 切换图层
    const toggleLayer = (layer) => {
      currentLayer.value = layer
      // 实现图层切换逻辑
      if (map) {
        map.eachLayer((layer) => {
          if (layer instanceof L.TileLayer) {
            map.removeLayer(layer)
          }
        })

        if (currentLayer.value === 'satellite') {
          L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles © Esri'
          }).addTo(map)
        } else {
          L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
          }).addTo(map)
        }
      }
    }

    // 其他功能
    const toggleMenu = () => {
      console.log('切换菜单')
    }

    const favoriteParking = () => {
      console.log('收藏停车场')
      alert('收藏功能开发中...')
    }

    const navigateToParking = () => {
      if (selectedParking.value) {
        const coords = selectedParking.value.coordinates
        window.open(`https://maps.google.com/maps?daddr=${coords[0]},${coords[1]}`, '_blank')
      }
    }

    const bookParking = async () => {
      if (!selectedParking.value) return

      try {
        const response = await axios.post(`${API_BASE}/parking-sessions`, {
          parking_lot_id: selectedParking.value.id,
          user_id: 'user_' + Date.now() // 简单的用户ID生成
        })

        if (response.data.success) {
          alert(`预订成功！停车会话ID: ${response.data.data.id}`)
          // 更新可用车位数据
          selectedParking.value.available -= 1
          loadParkingData() // 刷新数据
        } else {
          alert(`预订失败: ${response.data.error}`)
        }
      } catch (error) {
        console.error('预订失败:', error)
        alert('预订功能暂时不可用')
      }
    }

    onMounted(() => {
      initMap()
    })

    onUnmounted(() => {
      stopRealTimeUpdates()
    })

    return {
      searchQuery,
      selectedParking,
      loading,
      currentLayer,
      mapContainer,
      nearbyParkingCount,
      availableSpaces,
      selectParking,
      closeDetails,
      centerOnUser,
      onSearch,
      clearSearch,
      zoomIn,
      zoomOut,
      toggleLayer,
      toggleMenu,
      favoriteParking,
      navigateToParking,
      bookParking
    }
  }
}
</script>

<style scoped>
.parking-app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: #2c3e50;
  color: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.menu-btn, .user-location-btn {
  background: none;
  border: none;
  color: white;
  font-size: 18px;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: background 0.2s;
}

.menu-btn:hover, .user-location-btn:hover {
  background: rgba(255,255,255,0.1);
}

.app-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.search-container {
  padding: 15px;
  background: white;
  border-bottom: 1px solid #eee;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  background: #f8f9fa;
  border-radius: 25px;
  padding: 0 15px;
}

.search-icon {
  color: #666;
  margin-right: 10px;
}

.search-input {
  flex: 1;
  border: none;
  background: none;
  padding: 12px 0;
  font-size: 16px;
  outline: none;
}

.clear-btn {
  background: none;
  border: none;
  font-size: 20px;
  color: #666;
  cursor: pointer;
  padding: 0 5px;
}

.map-container {
  flex: 1;
  position: relative;
}

#map {
  width: 100%;
  height: 100%;
}

.map-controls {
  position: absolute;
  top: 20px;
  right: 20px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  z-index: 1000;
}

.control-btn {
  width: 40px;
  height: 40px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 18px;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: all 0.2s;
}

.control-btn:hover {
  background: #f0f0f0;
  transform: translateY(-1px);
}

.layer-toggle {
  position: absolute;
  top: 20px;
  left: 20px;
  display: flex;
  gap: 5px;
  z-index: 1000;
}

.layer-btn {
  padding: 8px 15px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 20px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.layer-btn.active {
  background: #3498db;
  color: white;
  border-color: #3498db;
}

.bottom-panel {
  background: white;
  border-top: 1px solid #eee;
  max-height: 300px;
  overflow-y: auto;
  transition: max-height 0.3s ease;
}

.bottom-panel.expanded {
  max-height: 500px;
}

.panel-summary {
  padding: 20px;
}

.panel-summary h3 {
  margin: 0 0 15px 0;
  color: #2c3e50;
}

.quick-stats {
  display: flex;
  gap: 30px;
}

.stat {
  text-align: center;
}

.stat-number {
  display: block;
  font-size: 24px;
  font-weight: bold;
  color: #3498db;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.parking-details {
  padding: 20px;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.close-btn, .favorite-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: background 0.2s;
}

.close-btn:hover, .favorite-btn:hover {
  background: #f0f0f0;
}

.detail-header h3 {
  margin: 0;
  color: #2c3e50;
}

.parking-image img {
  width: 100%;
  height: 150px;
  object-fit: cover;
  border-radius: 8px;
  margin-bottom: 15px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.info-label {
  font-size: 12px;
  color: #666;
  text-transform: uppercase;
}

.info-value {
  font-weight: 600;
  color: #2c3e50;
}

.info-value.available {
  color: #27ae60;
}

.info-value.price {
  color: #e74c3c;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.action-btn {
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.primary {
  background: #3498db;
  color: white;
}

.action-btn.secondary {
  background: #ecf0f1;
  color: #2c3e50;
}

.action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255,255,255,0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 自定义标记样式 */
:global(.parking-marker) {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

:global(.parking-count) {
  color: white;
  font-weight: bold;
  font-size: 12px;
}

:global(.user-marker) {
  font-size: 20px;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
}

:global(.custom-cluster) {
  background: #3498db;
  border-radius: 50%;
  text-align: center;
  color: white;
  font-weight: bold;
  border: 2px solid white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

:global(.custom-cluster div) {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
