<template>
  <div class="melbourne-parking-app">
    <!-- 顶部搜索栏 -->
    <div class="search-container">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by postcode or suburb (e.g., 3000, Melbourne CBD)"
          class="search-input"
          @keyup.enter="performSearch"
          @input="onSearchInput"
        />
        <button v-if="searchQuery" @click="clearSearch" class="clear-btn">×</button>
      </div>

      <!-- 过滤按钮 -->
      <div class="filter-buttons">
        <button
          @click="setStatusFilter('all')"
          :class="['filter-btn', { active: statusFilter === 'all' }]"
        >
          All Spaces
        </button>
        <button
          @click="setStatusFilter('available')"
          :class="['filter-btn', { active: statusFilter === 'available' }]"
        >
          Available Only
        </button>
        <button
          @click="setStatusFilter('occupied')"
          :class="['filter-btn', { active: statusFilter === 'occupied' }]"
        >
          Occupied Only
        </button>
      </div>
    </div>

    <!-- 统计信息栏 -->
    <div class="stats-bar" v-if="parkingStats">
      <div class="stat-item">
        <span class="stat-number">{{ parkingStats.total_sensors }}</span>
        <span class="stat-label">Total Sensors</span>
      </div>
      <div class="stat-item available">
        <span class="stat-number">{{ parkingStats.available }}</span>
        <span class="stat-label">Available</span>
      </div>
      <div class="stat-item occupied">
        <span class="stat-number">{{ parkingStats.occupied }}</span>
        <span class="stat-label">Occupied</span>
      </div>
      <div class="stat-item">
        <span class="stat-number">{{ parkingStats.occupancy_rate }}%</span>
        <span class="stat-label">Occupancy Rate</span>
      </div>
    </div>

    <!-- 地图容器 -->
    <div class="map-container">
      <div id="melbourne-map" class="leaflet-map"></div>

      <!-- 实时数据状态指示器 -->
      <div class="realtime-status">
        <div :class="['status-dot', connectionStatus]"></div>
        <span class="status-text">{{ connectionStatusText }}</span>
      </div>

      <!-- 地图控制按钮 -->
      <div class="map-controls">
        <button @click="refreshData" class="control-btn" :disabled="isLoading">
          <span class="btn-icon">🔄</span>
          {{ isLoading ? 'Loading...' : 'Refresh' }}
        </button>
        <button @click="locateUser" class="control-btn">
          <span class="btn-icon">📍</span>
          My Location
        </button>
        <button @click="toggleMapStyle" class="control-btn">
          <span class="btn-icon">🗺️</span>
          {{ mapStyle === 'street' ? 'Satellite' : 'Street' }}
        </button>
      </div>

      <!-- 加载覆盖层 -->
      <div v-if="isLoading" class="loading-overlay">
        <div class="loading-spinner"></div>
        <p class="loading-text">{{ loadingMessage }}</p>
      </div>
    </div>

    <!-- 停车位详情面板 -->
    <div v-if="selectedParking" class="details-panel" :class="{ visible: selectedParking }">
      <div class="panel-header">
        <h3 class="panel-title">
          Space {{ selectedParking.kerbside_id || selectedParking.id }}
        </h3>
        <button @click="closePanel" class="close-btn">✕</button>
      </div>

      <div class="panel-content">
        <div class="status-indicator" :class="getStatusClass(selectedParking.status)">
          <span class="status-dot"></span>
          <span class="status-text">{{ getStatusText(selectedParking.status) }}</span>
        </div>

        <div class="details-grid">
          <div class="detail-item" v-if="selectedParking.zone_number">
            <span class="detail-label">Zone</span>
            <span class="detail-value">{{ selectedParking.zone_number }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Location</span>
            <span class="detail-value">{{ formatCoordinates(selectedParking.coordinates) }}</span>
          </div>

          <div class="detail-item" v-if="selectedParking.last_updated">
            <span class="detail-label">Last Update</span>
            <span class="detail-value">{{ formatTimestamp(selectedParking.last_updated) }}</span>
          </div>
        </div>

        <div class="action-buttons">
          <button @click="getDirections" class="action-btn primary">
            <span class="btn-icon">🧭</span>
            Get Directions
          </button>
          <button @click="shareLocation" class="action-btn secondary">
            <span class="btn-icon">📤</span>
            Share Location
          </button>
        </div>
      </div>
    </div>

    <!-- 状态消息 -->
    <div v-if="statusMessage" class="status-message" :class="messageType">
      {{ statusMessage }}
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import axios from 'axios'

export default {
  name: 'MelbourneParkingMap',
  setup() {
    // 响应式数据
    const selectedParking = ref(null)
    const parkingData = ref([])
    const parkingStats = ref(null)
    const searchQuery = ref('')
    const statusFilter = ref('all')
    const isLoading = ref(false)
    const isSearching = ref(false)
    const statusMessage = ref('')
    const messageType = ref('info')
    const loadingMessage = ref('Loading parking data...')
    const userLocation = ref(null)
    const connectionStatus = ref('connected')
    const mapStyle = ref('street')

    // 地图变量
    let map = null
    let markersLayer = null
    let userMarker = null
    let refreshInterval = null

    // API配置 - 修复前端到后端的连接
    const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://localhost:5001'

    // 计算属性
    const connectionStatusText = computed(() => {
      switch (connectionStatus.value) {
        case 'connected': return 'Live Data Connected'
        case 'connecting': return 'Connecting...'
        case 'disconnected': return 'Connection Lost'
        default: return 'Unknown Status'
      }
    })

    // 初始化地图
    const initMap = async () => {
      try {
        if (typeof window.L === 'undefined') {
          throw new Error('Leaflet library not loaded')
        }

        // 创建地图，中心为墨尔本CBD
        map = window.L.map('melbourne-map', {
          center: [-37.8136, 144.9631],
          zoom: 14,
          zoomControl: false,
          attributionControl: true
        })

        // 添加瓦片图层
        updateMapStyle()

        // 创建标记图层
        markersLayer = window.L.layerGroup().addTo(map)

        console.log('🗺️ Map initialized successfully')

        // 加载初始数据
        await Promise.all([
          fetchParkingData(),
          fetchParkingStats()
        ])

      } catch (error) {
        console.error('❌ Map initialization failed:', error)
        showMessage('Failed to initialize map', 'error')
      }
    }

    // 获取实时停车数据
    const fetchParkingData = async (searchParams = {}) => {
      try {
        isLoading.value = true
        connectionStatus.value = 'connecting'
        loadingMessage.value = 'Fetching real-time parking data...'

        const params = {
          status: statusFilter.value !== 'all' ? statusFilter.value : undefined,
          ...searchParams
        }

        const response = await axios.get(`${API_BASE}/api/parking/live`, {
          params,
          timeout: 15000
        })

        if (response.data.success) {
          parkingData.value = response.data.data
          updateMapMarkers()
          connectionStatus.value = 'connected'
          showMessage(`Found ${response.data.count} parking spaces`, 'success')
        } else {
          throw new Error(response.data.error || 'Failed to fetch parking data')
        }

      } catch (error) {
        console.error('❌ Error fetching parking data:', error)
        connectionStatus.value = 'disconnected'
        showMessage('Unable to fetch real-time data. Please try again.', 'error')

        // 使用演示数据作为后备
        parkingData.value = getDemoData()
        updateMapMarkers()

      } finally {
        isLoading.value = false
      }
    }

    // 获取停车统计
    const fetchParkingStats = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/stats`)
        if (response.data.success) {
          parkingStats.value = response.data.stats
        }
      } catch (error) {
        console.error('❌ Error fetching stats:', error)
      }
    }

    // 更新地图标记
    const updateMapMarkers = () => {
      if (!markersLayer || !map) return

      // 清除现有标记
      markersLayer.clearLayers()

      // 添加停车标记
      parkingData.value.forEach(parking => {
        const [lat, lng] = parking.coordinates

        // 根据状态创建自定义图标
        const isAvailable = parking.status === 'Unoccupied'
        const iconClass = isAvailable ? 'available' : 'occupied'
        const iconEmoji = isAvailable ? '🅿️' : '🚫'

        const customIcon = window.L.divIcon({
          html: `<div class="parking-marker ${iconClass}">
                   <span class="marker-icon">${iconEmoji}</span>
                 </div>`,
          className: 'custom-marker-container',
          iconSize: [32, 32],
          iconAnchor: [16, 16]
        })

        const marker = window.L.marker([lat, lng], { icon: customIcon })
          .addTo(markersLayer)
          .on('click', () => selectParking(parking))

        // 添加弹出窗口
        const popupContent = `
          <div class="marker-popup">
            <strong>Space ${parking.kerbside_id || parking.id}</strong><br>
            Status: <span class="${iconClass}">${parking.status}</span><br>
            ${parking.zone_number ? `Zone: ${parking.zone_number}` : ''}
          </div>
        `
        marker.bindPopup(popupContent)
      })
    }

    // 搜索功能
    const performSearch = async () => {
      if (!searchQuery.value.trim()) {
        showMessage('Please enter a search term', 'warning')
        return
      }

      try {
        isSearching.value = true
        loadingMessage.value = 'Searching parking spaces...'

        const response = await axios.get(`${API_BASE}/api/parking/search`, {
          params: { q: searchQuery.value.trim() }
        })

        if (response.data.success) {
          parkingData.value = response.data.data

          // 将地图中心移动到搜索结果
          if (response.data.center) {
            map.setView(response.data.center, 15)
          }

          updateMapMarkers()
          showMessage(`Found ${response.data.count} parking spaces near "${response.data.query}"`, 'success')
        }

      } catch (error) {
        console.error('❌ Search error:', error)
        showMessage('Search failed. Please try again.', 'error')
      } finally {
        isSearching.value = false
      }
    }

    const onSearchInput = () => {
      // 可以添加实时搜索建议功能
    }

    const clearSearch = () => {
      searchQuery.value = ''
      fetchParkingData()
    }

    // ��滤功能
    const setStatusFilter = (filter) => {
      statusFilter.value = filter
      fetchParkingData()
    }

    // 工具函数
    const selectParking = (parking) => {
      selectedParking.value = parking
    }

    const closePanel = () => {
      selectedParking.value = null
    }

    const refreshData = async () => {
      await Promise.all([
        fetchParkingData(),
        fetchParkingStats()
      ])
    }

    const locateUser = () => {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            const { latitude, longitude } = position.coords
            userLocation.value = [latitude, longitude]

            // 添加用户标记
            if (userMarker) {
              map.removeLayer(userMarker)
            }

            userMarker = window.L.marker([latitude, longitude], {
              icon: window.L.divIcon({
                html: '<div class="user-marker">📍</div>',
                className: 'user-marker-container',
                iconSize: [24, 24],
                iconAnchor: [12, 12]
              })
            }).addTo(map)

            map.setView([latitude, longitude], 16)
            showMessage('Location found!', 'success')
          },
          (error) => {
            showMessage('Unable to get your location', 'error')
          }
        )
      } else {
        showMessage('Geolocation not supported', 'error')
      }
    }

    const toggleMapStyle = () => {
      mapStyle.value = mapStyle.value === 'street' ? 'satellite' : 'street'
      updateMapStyle()
    }

    const updateMapStyle = () => {
      if (!map) return

      // 移除现有瓦片图层
      map.eachLayer((layer) => {
        if (layer instanceof window.L.TileLayer) {
          map.removeLayer(layer)
        }
      })

      // 添加新的瓦片图层
      if (mapStyle.value === 'satellite') {
        window.L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
          attribution: 'Tiles © Esri'
        }).addTo(map)
      } else {
        window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors'
        }).addTo(map)
      }
    }

    const getDirections = () => {
      if (selectedParking.value && selectedParking.value.coordinates) {
        const [lat, lng] = selectedParking.value.coordinates
        const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
        window.open(url, '_blank')
      }
    }

    const shareLocation = () => {
      if (selectedParking.value && navigator.share) {
        navigator.share({
          title: 'Melbourne Parking Space',
          text: `Found a parking space: ${selectedParking.value.kerbside_id}`,
          url: window.location.href
        })
      } else {
        // 复制到剪贴板作为后备
        const text = `Parking Space ${selectedParking.value.kerbside_id} - ${selectedParking.value.coordinates.join(', ')}`
        navigator.clipboard.writeText(text).then(() => {
          showMessage('Location copied to clipboard', 'success')
        })
      }
    }

    const getStatusClass = (status) => {
      return status === 'Unoccupied' ? 'available' : 'occupied'
    }

    const getStatusText = (status) => {
      return status === 'Unoccupied' ? 'Available' : 'Occupied'
    }

    const formatCoordinates = (coords) => {
      if (!coords || coords.length < 2) return 'N/A'
      return `${coords[0].toFixed(4)}, ${coords[1].toFixed(4)}`
    }

    const formatTimestamp = (timestamp) => {
      if (!timestamp) return 'N/A'
      return new Date(timestamp).toLocaleString()
    }

    const showMessage = (message, type = 'info') => {
      statusMessage.value = message
      messageType.value = type
      setTimeout(() => {
        statusMessage.value = ''
      }, 5000)
    }

    const getDemoData = () => [
      {
        id: 'demo_1',
        kerbside_id: 'DEMO_001',
        zone_number: '1A',
        status: 'Unoccupied',
        coordinates: [-37.8136, 144.9631],
        last_updated: new Date().toISOString()
      }
    ]

    // 生命周期钩子
    onMounted(() => {
      initMap()

      // 设置自动刷新
      refreshInterval = setInterval(() => {
        fetchParkingData()
        fetchParkingStats()
      }, 60000) // 每分钟刷新一次
    })

    onUnmounted(() => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
    })

    return {
      // 数据
      selectedParking,
      parkingData,
      parkingStats,
      searchQuery,
      statusFilter,
      isLoading,
      isSearching,
      statusMessage,
      messageType,
      loadingMessage,
      connectionStatus,
      connectionStatusText,
      mapStyle,

      // 方法
      performSearch,
      onSearchInput,
      clearSearch,
      setStatusFilter,
      selectParking,
      closePanel,
      refreshData,
      locateUser,
      toggleMapStyle,
      getDirections,
      shareLocation,
      getStatusClass,
      getStatusText,
      formatCoordinates,
      formatTimestamp
    }
  }
}
</script>

<style scoped>
/* 主应用样式 */
.melbourne-parking-app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: #f5f7fa;
}

/* 搜索容器 */
.search-container {
  background: white;
  padding: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  z-index: 1000;
}

.search-box {
  display: flex;
  align-items: center;
  background: #f8f9fa;
  border-radius: 25px;
  padding: 0.5rem 1rem;
  margin-bottom: 1rem;
  border: 2px solid transparent;
  transition: border-color 0.3s;
}

.search-box:focus-within {
  border-color: #007bff;
}

.search-icon {
  color: #6c757d;
  margin-right: 0.5rem;
}

.search-input {
  flex: 1;
  border: none;
  background: none;
  padding: 0.5rem 0;
  font-size: 1rem;
  outline: none;
}

.clear-btn {
  background: none;
  border: none;
  color: #6c757d;
  cursor: pointer;
  font-size: 1.2rem;
  padding: 0.2rem;
}

.filter-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 0.5rem 1rem;
  border: 2px solid #dee2e6;
  background: white;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 0.9rem;
  font-weight: 500;
}

.filter-btn:hover {
  border-color: #007bff;
}

.filter-btn.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

/* 统计栏 */
.stats-bar {
  background: white;
  padding: 1rem;
  display: flex;
  justify-content: space-around;
  border-bottom: 1px solid #dee2e6;
}

.stat-item {
  text-align: center;
}

.stat-number {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: #212529;
}

.stat-label {
  font-size: 0.8rem;
  color: #6c757d;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-item.available .stat-number {
  color: #28a745;
}

.stat-item.occupied .stat-number {
  color: #dc3545;
}

/* 地图容器 */
.map-container {
  flex: 1;
  position: relative;
  background: #e9ecef;
}

.leaflet-map {
  width: 100%;
  height: 100%;
}

/* 实时状态指示器 */
.realtime-status {
  position: absolute;
  top: 1rem;
  left: 1rem;
  background: white;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  z-index: 1000;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-dot.connected {
  background: #28a745;
}

.status-dot.connecting {
  background: #ffc107;
}

.status-dot.disconnected {
  background: #dc3545;
}

.status-text {
  font-size: 0.9rem;
  font-weight: 500;
}

/* 地图控制按钮 */
.map-controls {
  position: absolute;
  top: 1rem;
  right: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  z-index: 1000;
}

.control-btn {
  background: white;
  border: none;
  padding: 0.75rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  min-width: 120px;
  justify-content: center;
}

.control-btn:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  transform: translateY(-1px);
}

.control-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* 详情面板 */
.details-panel {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  border-radius: 16px 16px 0 0;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
  transform: translateY(100%);
  transition: transform 0.3s ease;
  z-index: 1000;
  max-height: 50vh;
  overflow-y: auto;
}

.details-panel.visible {
  transform: translateY(0);
}

.panel-header {
  padding: 1.5rem 1.5rem 1rem;
  border-bottom: 1px solid #dee2e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #212529;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6c757d;
  padding: 0.5rem;
  border-radius: 50%;
  transition: background-color 0.3s;
}

.close-btn:hover {
  background: #f8f9fa;
}

.panel-content {
  padding: 1.5rem;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  padding: 0.75rem;
  border-radius: 8px;
  font-weight: 500;
}

.status-indicator.available {
  background: #d4edda;
  color: #155724;
}

.status-indicator.occupied {
  background: #f8d7da;
  color: #721c24;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.details-grid {
  display: grid;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-label {
  font-weight: 500;
  color: #6c757d;
}

.detail-value {
  color: #212529;
  font-weight: 500;
}

.action-buttons {
  display: flex;
  gap: 0.75rem;
}

.action-btn {
  flex: 1;
  padding: 0.75rem 1rem;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.action-btn.primary {
  background: #007bff;
  color: white;
}

.action-btn.primary:hover {
  background: #0056b3;
}

.action-btn.secondary {
  background: #f8f9fa;
  color: #495057;
  border: 1px solid #dee2e6;
}

.action-btn.secondary:hover {
  background: #e9ecef;
}

/* 加载覆盖层 */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f4f6;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-text {
  margin-top: 1rem;
  color: #6c757d;
  font-weight: 500;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 状态消息 */
.status-message {
  position: fixed;
  top: 1rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 500;
  z-index: 3000;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  animation: slideIn 0.3s ease;
}

.status-message.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status-message.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.status-message.warning {
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffeaa7;
}

.status-message.info {
  background: #d1ecf1;
  color: #0c5460;
  border: 1px solid #bee5eb;
}

@keyframes slideIn {
  from {
    transform: translate(-50%, -100%);
    opacity: 0;
  }
  to {
    transform: translate(-50%, 0);
    opacity: 1;
  }
}

/* 自定义地图标记样式 */
:deep(.custom-marker-container) {
  background: none !important;
  border: none !important;
}

:deep(.parking-marker) {
  background: white;
  border-radius: 50%;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  font-size: 18px;
  transition: transform 0.2s;
}

:deep(.parking-marker:hover) {
  transform: scale(1.1);
}

:deep(.parking-marker.available) {
  border: 3px solid #28a745;
}

:deep(.parking-marker.occupied) {
  border: 3px solid #dc3545;
}

:deep(.user-marker-container) {
  background: none !important;
  border: none !important;
}

:deep(.user-marker) {
  font-size: 24px;
  text-shadow: 0 2px 4px rgba(0,0,0,0.3);
}

/* 弹出窗口样式 */
:deep(.leaflet-popup-content) {
  margin: 12px;
  line-height: 1.4;
}

:deep(.marker-popup) {
  text-align: center;
  font-size: 14px;
}

:deep(.marker-popup .available) {
  color: #28a745;
  font-weight: bold;
}

:deep(.marker-popup .occupied) {
  color: #dc3545;
  font-weight: bold;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .search-container {
    padding: 0.75rem;
  }

  .stats-bar {
    padding: 0.75rem;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .stat-item {
    flex: 1;
    min-width: calc(50% - 0.25rem);
  }

  .filter-buttons {
    justify-content: center;
  }

  .details-panel {
    max-height: 60vh;
  }

  .action-buttons {
    flex-direction: column;
  }

  .map-controls {
    flex-direction: row;
    top: auto;
    bottom: 1rem;
    right: 1rem;
    left: 1rem;
  }

  .control-btn {
    flex: 1;
    min-width: auto;
  }
}
</style>
