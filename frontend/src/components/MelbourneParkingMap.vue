<template>
  <div class="melbourne-parking-app">
    <!-- top search bar -->
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

      <!-- 停车类型筛选按钮 -->
      <div class="parking-type-buttons">
        <button
          @click="setParkingTypeFilter('all')"
          :class="['type-btn', { active: parkingTypeFilter === 'all' }]"
        >
          <span class="btn-icon">🅿️</span>
          All Parking
        </button>
        <button
          @click="setParkingTypeFilter('on-street')"
          :class="['type-btn', { active: parkingTypeFilter === 'on-street' }]"
        >
          <span class="btn-icon">🚗</span>
          On-Street
        </button>
        <button
          @click="setParkingTypeFilter('off-street')"
          :class="['type-btn', { active: parkingTypeFilter === 'off-street' }]"
        >
          <span class="btn-icon">🏢</span>
          Off-Street
        </button>
      </div>

      <!-- 状态过滤按钮 -->
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
        <span class="stat-number">{{ parkingStats.total_parking_spaces || parkingStats.total_sensors }}</span>
        <span class="stat-label">Total Spaces</span>
      </div>
      <div class="stat-item on-street">
        <span class="stat-number">{{ parkingStats.on_street_spaces || parkingStats.available }}</span>
        <span class="stat-label">On-Street</span>
      </div>
      <div class="stat-item off-street">
        <span class="stat-number">{{ parkingStats.off_street_spaces || parkingStats.occupied }}</span>
        <span class="stat-label">Off-Street</span>
      </div>
      <div class="stat-item">
        <span class="stat-number">{{ parkingStats.on_street_occupancy_rate || parkingStats.occupancy_rate }}%</span>
        <span class="stat-label">Occupancy Rate</span>
      </div>
    </div>

    <!-- the container of maps -->
    <div class="map-container">
      <div id="melbourne-map" class="leaflet-map"></div>

      <!-- real-time status -->
      <div class="realtime-status">
        <div :class="['status-dot', connectionStatus]"></div>
        <span class="status-text">{{ connectionStatusText }}</span>
      </div>

      <!-- map-controls-button -->
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

      <!-- load-overlay -->
      <div v-if="isLoading" class="loading-overlay">
        <div class="loading-spinner"></div>
        <p class="loading-text">{{ loadingMessage }}</p>
      </div>
    </div>

    <!-- statusMessage -->
    <div v-if="statusMessage" class="status-message" :class="messageType">
      {{ statusMessage }}
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import axios from 'axios'
import L from 'leaflet'

// 修复Leaflet默认图标问题
import 'leaflet/dist/leaflet.css'
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

export default {
  name: 'MelbourneParkingMap',
  setup() {
    // 响应式数据
    const selectedParking = ref(null)
    const parkingData = ref([])
    const parkingStats = ref(null)
    const searchQuery = ref('')
    const statusFilter = ref('all')
    const parkingTypeFilter = ref('all') // 新增：停车类型筛选
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

    // API配置 - 修正API端口
    const API_BASE = import.meta.env.VITE_API_BASE_URL ||
                     (import.meta.env.DEV ? 'http://localhost:8888' : '')

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
        console.log('🗺️ Initializing map...')

        // 创建地图，中心为墨尔本CBD
        map = L.map('melbourne-map', {
          center: [-37.8136, 144.9631],
          zoom: 14,
          zoomControl: false,
          attributionControl: true
        })

        // 添加瓦片图层
        updateMapStyle()

        // 创建标记图层
        markersLayer = L.layerGroup().addTo(map)

        console.log('🗺️ Map initialized successfully')

        // 加载初始数据
        await Promise.all([
          fetchParkingData(),
          fetchParkingStats()
        ])

      } catch (error) {
        console.error('❌ Map initialization failed:', error)
        showMessage('Failed to initialize map: ' + error.message, 'error')
      }
    }

    // 更新地图样式
    const updateMapStyle = () => {
      if (!map) return

      // 移除现有图层
      map.eachLayer((layer) => {
        if (layer._url) { // 这是瓦片图层
          map.removeLayer(layer)
        }
      })

      // 添加新的瓦片图层
      const tileLayer = mapStyle.value === 'street' ?
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors'
        }) :
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
          attribution: '© Esri'
        })

      tileLayer.addTo(map)
    }

    // 获取实时停车数据
    const fetchParkingData = async (searchParams = {}) => {
      try {
        isLoading.value = true
        loadingMessage.value = 'Loading parking data...'

        console.log('📡 Fetching parking data from:', `${API_BASE}/api/parking/search`)

        const params = new URLSearchParams({
          limit: '500',
          ...searchParams
        })

        const response = await axios.get(`${API_BASE}/api/parking/search?${params}`)
        parkingData.value = response.data

        console.log(`✅ Loaded ${parkingData.value.length} parking facilities`)
        updateMarkers()
        showMessage(`Loaded ${parkingData.value.length} parking facilities`, 'success')

      } catch (error) {
        console.error('❌ Error fetching parking data:', error)
        showMessage('Failed to load parking data', 'error')
      } finally {
        isLoading.value = false
      }
    }

    // 获取停车统计信息
    const fetchParkingStats = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/parking/stats`)
        parkingStats.value = response.data
        console.log('📊 Parking stats loaded:', parkingStats.value)
      } catch (error) {
        console.error('❌ Error fetching parking stats:', error)
      }
    }

    // 更新地图标记
    const updateMarkers = () => {
      if (!map || !markersLayer) return

      // 清除现有标记
      markersLayer.clearLayers()

      // 过滤数据
      const filteredData = parkingData.value.filter(item => {
        if (parkingTypeFilter.value !== 'all') {
          // 根据停车类型过滤
          return true // 暂时显示所有数据
        }
        return true
      })

      // 添加停车场针脚标记
      filteredData.forEach(parking => {
        if (parking.latitude && parking.longitude) {
          // 根据停车位数量确定标记颜色
          const spaces = parking.parking_spaces || 0
          let pinColor = '#28a745' // 默认绿色

          if (spaces > 500) {
            pinColor = '#dc3545' // 红色 - 大型停车场
          } else if (spaces > 100) {
            pinColor = '#fd7e14' // 橙色 - 中型停车场
          } else if (spaces > 50) {
            pinColor = '#ffc107' // 黄色 - 小型停车场
          }
          // 50以下保持绿色

          // 创建自定义针脚图标
          const pinIcon = L.divIcon({
            html: `
              <div class="custom-pin" style="--pin-color: ${pinColor}">
                <div class="pin-head">
                  <div class="pin-content">
                    <span class="parking-icon">🅿️</span>
                    <span class="spaces-count">${spaces}</span>
                  </div>
                </div>
                <div class="pin-point"></div>
              </div>
            `,
            className: 'custom-pin-container',
            iconSize: [40, 50],
            iconAnchor: [20, 50],
            popupAnchor: [0, -50]
          })

          const marker = L.marker([parking.latitude, parking.longitude], {
            icon: pinIcon
          })

          // 创建详细的弹出窗口内容
          const popupContent = `
            <div class="parking-popup">
              <div class="popup-header">
                <h4 class="popup-title">🅿️ 停车场信息</h4>
                <div class="popup-badge" style="background-color: ${pinColor}">
                  ${spaces} 位
                </div>
              </div>

              <div class="popup-body">
                <div class="info-row">
                  <span class="info-label">📍 地址:</span>
                  <span class="info-value">${parking.building_address || '未知地址'}</span>
                </div>

                <div class="info-row">
                  <span class="info-label">🏢 类型:</span>
                  <span class="info-value">${parking.parking_type || '未知'}</span>
                </div>

                <div class="info-row">
                  <span class="info-label">🗺️ 区域:</span>
                  <span class="info-value">${parking.clue_small_area || '未知区域'}</span>
                </div>

                <div class="info-row">
                  <span class="info-label">📊 停车位:</span>
                  <span class="info-value spaces-highlight">${spaces} 个</span>
                </div>

                <div class="info-row">
                  <span class="info-label">🧭 坐标:</span>
                  <span class="info-value">${parseFloat(parking.latitude).toFixed(4)}, ${parseFloat(parking.longitude).toFixed(4)}</span>
                </div>
              </div>

              <div class="popup-actions">
                <button onclick="getDirections(${parking.latitude}, ${parking.longitude})" class="popup-btn primary">
                  🧭 导航
                </button>
                <button onclick="selectParkingDetails(${parking.id})" class="popup-btn secondary">
                  📋 详情
                </button>
              </div>
            </div>
          `

          marker.bindPopup(popupContent, {
            maxWidth: 300,
            className: 'custom-parking-popup'
          })

          marker.on('click', () => {
            selectedParking.value = {
              ...parking,
              coordinates: [parking.latitude, parking.longitude]
            }
          })

          markersLayer.addLayer(marker)
        }
      })

      console.log(`🗺️ Added ${filteredData.length} pin markers to map`)
    }

    // 全局函数供弹出窗口使用
    window.getDirections = (lat, lng) => {
      const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
      window.open(url, '_blank')
    }

    window.selectParkingDetails = (parkingId) => {
      const parking = parkingData.value.find(p => p.id === parkingId)
      if (parking) {
        selectedParking.value = {
          ...parking,
          coordinates: [parking.latitude, parking.longitude]
        }
      }
    }

    // 显示消息
    const showMessage = (message, type = 'info') => {
      statusMessage.value = message
      messageType.value = type
      setTimeout(() => {
        statusMessage.value = ''
      }, 5000)
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
    // 停车类型筛选功能
    const setParkingTypeFilter = (filter) => {
      parkingTypeFilter.value = filter
      fetchParkingData()
    }

    // 状态筛选功能
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

            userMarker = L.marker([latitude, longitude], {
              icon: L.divIcon({
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

    // 生命周期钩子
    onMounted(() => {
      // 延迟初始化地图，确保DOM已渲染
      setTimeout(initMap, 100)

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
      if (map) {
        map.remove()
      }
    })

    // 返回组件需要的数据和方法
    return {
      // 数据
      selectedParking,
      parkingData,
      parkingStats,
      searchQuery,
      statusFilter,
      parkingTypeFilter,
      isLoading,
      statusMessage,
      messageType,
      loadingMessage,
      connectionStatus,
      mapStyle,
      connectionStatusText,

      // 方法
      initMap,
      fetchParkingData,
      updateMarkers,
      showMessage,

      // 事件处理方法（需要实现）
      performSearch: () => {
        if (searchQuery.value.trim()) {
          fetchParkingData({ suburb: searchQuery.value })
        }
      },
      clearSearch: () => {
        searchQuery.value = ''
        fetchParkingData()
      },
      setParkingTypeFilter: (type) => {
        parkingTypeFilter.value = type
        updateMarkers()
      },
      setStatusFilter: (status) => {
        statusFilter.value = status
        updateMarkers()
      },
      refreshData: () => {
        fetchParkingData()
        fetchParkingStats()
      },
      toggleMapStyle: () => {
        mapStyle.value = mapStyle.value === 'street' ? 'satellite' : 'street'
        updateMapStyle()
      },
      locateUser: () => {
        // 实现用户定位功能
        console.log('Locating user...')
      },
      closePanel: () => {
        selectedParking.value = null
      },
      getStatusClass: (status) => status || 'unknown',
      getStatusText: (status) => status || 'Unknown',
      formatCoordinates: (coords) => coords ? `${coords.lat}, ${coords.lon}` : 'N/A',
      formatTimestamp: (timestamp) => timestamp ? new Date(timestamp).toLocaleString() : 'N/A',
      getDirections: () => console.log('Getting directions...'),
      shareLocation: () => console.log('Sharing location...'),
      onSearchInput: () => {
        // 可以实现实时搜索建议
      }
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

/* 停车类型筛选按钮 */
.parking-type-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.type-btn {
  padding: 0.75rem 1.5rem;
  border: 2px solid #dee2e6;
  background: white;
  border-radius: 25px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 0.9rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 120px;
  justify-content: center;
}

.type-btn:hover {
  border-color: #28a745;
  transform: translateY(-1px);
}

.type-btn.active {
  background: #28a745;
  color: white;
  border-color: #28a745;
  box-shadow: 0 2px 8px rgba(40, 167, 69, 0.3);
}

.type-btn .btn-icon {
  font-size: 1.1rem;
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

.stat-item.on-street .stat-number {
  color: #007bff;
}

.stat-item.off-street .stat-number {
  color: #6f42c1;
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

/* status-message  */
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

:deep(.parking-marker.on-street) {
  background: linear-gradient(135deg, #e3f2fd, #bbdefb);
}

:deep(.parking-marker.off-street) {
  background: linear-gradient(135deg, #f3e5f5, #e1bee7);
}

:deep(.parking-marker .marker-type) {
  position: absolute;
  top: -2px;
  right: -2px;
  background: #007bff;
  color: white;
  border-radius: 50%;
  width: 12px;
  height: 12px;
  font-size: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
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

/* 自定义针脚标记样式 */
:deep(.custom-pin-container) {
  background: none !important;
  border: none !important;
}

:deep(.custom-pin) {
  position: relative;
  width: 40px;
  height: 50px;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: transform 0.3s ease;
  cursor: pointer;
}

:deep(.custom-pin:hover) {
  transform: scale(1.1);
  z-index: 1000;
}

:deep(.pin-head) {
  width: 32px;
  height: 32px;
  background: var(--pin-color);
  border-radius: 50%;
  border: 3px solid white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 2;
}

:deep(.pin-point) {
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 12px solid var(--pin-color);
  margin-top: -2px;
  z-index: 1;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

:deep(.pin-content) {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

:deep(.parking-icon) {
  font-size: 12px;
  line-height: 1;
  margin-bottom: 1px;
}

:deep(.spaces-count) {
  font-size: 8px;
  font-weight: bold;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
  line-height: 1;
}

/* 弹出窗口样式优化 */
:deep(.custom-parking-popup .leaflet-popup-content-wrapper) {
  border-radius: 12px;
  padding: 0;
  overflow: hidden;
}

:deep(.custom-parking-popup .leaflet-popup-content) {
  margin: 0;
  width: 280px !important;
}

:deep(.parking-popup) {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

:deep(.popup-header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

:deep(.popup-title) {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

:deep(.popup-badge) {
  background: rgba(255, 255, 255, 0.2);
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: bold;
  backdrop-filter: blur(10px);
}

:deep(.popup-body) {
  padding: 1rem;
  background: white;
}

:deep(.info-row) {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #f0f0f0;
}

:deep(.info-row:last-child) {
  border-bottom: none;
  margin-bottom: 0;
}

:deep(.info-label) {
  font-weight: 500;
  color: #666;
  font-size: 0.9rem;
  flex-shrink: 0;
  width: 80px;
}

:deep(.info-value) {
  color: #333;
  font-size: 0.9rem;
  text-align: right;
  flex: 1;
  word-break: break-word;
}

:deep(.spaces-highlight) {
  color: #28a745;
  font-weight: bold;
  font-size: 1rem;
}

:deep(.popup-actions) {
  padding: 1rem;
  background: #f8f9fa;
  display: flex;
  gap: 0.5rem;
  border-top: 1px solid #e9ecef;
}

:deep(.popup-btn) {
  flex: 1;
  padding: 0.6rem 1rem;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
}

:deep(.popup-btn.primary) {
  background: #007bff;
  color: white;
}

:deep(.popup-btn.primary:hover) {
  background: #0056b3;
  transform: translateY(-1px);
}

:deep(.popup-btn.secondary) {
  background: white;
  color: #495057;
  border: 1px solid #dee2e6;
}

:deep(.popup-btn.secondary:hover) {
  background: #e9ecef;
  transform: translateY(-1px);
}
</style>
