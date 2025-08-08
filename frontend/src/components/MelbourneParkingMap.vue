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

      <!-- 状态过滤按钮 - 简化为三个选项 -->
      <div class="filter-buttons">
        <button
          @click="setStatusFilter('all')"
          :class="['filter-btn', { active: statusFilter === 'all' }]"
        >
          All Spaces
        </button>
        <button
          @click="setStatusFilter('on-street')"
          :class="['filter-btn', { active: statusFilter === 'on-street' }]"
        >
          On-Street
        </button>
        <button
          @click="setStatusFilter('off-street')"
          :class="['filter-btn', { active: statusFilter === 'off-street' }]"
        >
          Off-Street
        </button>
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

    // API配置 - 确保使用正确的端口8889
    const API_BASE = 'http://localhost:8889'

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

        console.log('📡 Fetching parking data from both sources')
        console.log('📋 Search params:', searchParams)

        // 同时获取off-street和on-street数据
        const promises = []

        // Off-street停车场数据
        let offStreetParams = {
          limit: '500',
          ...searchParams
        }
        promises.push(
          axios.get(`${API_BASE}/api/parking/search?${new URLSearchParams(offStreetParams)}`)
            .then(response => ({
              type: 'off-street',
              data: response.data.map(item => ({
                ...item,
                data_source: 'off-street',
                parking_type: 'Off-Street'
              }))
            }))
            .catch(error => {
              console.error('❌ Error fetching off-street data:', error)
              return { type: 'off-street', data: [] }
            })
        )

        // On-street传感器数据 - 限制为100个
        let onStreetParams = {
          limit: '100',  // 只获取100个on-street传感器
          active_hours: '24',
          ...searchParams
        }
        promises.push(
          axios.get(`${API_BASE}/api/sensors/sensors?${new URLSearchParams(onStreetParams)}`)
            .then(response => ({
              type: 'on-street',
              data: response.data.map(item => ({
                ...item,
                data_source: 'on-street',
                parking_type: 'On-Street',
                parking_spaces: 1 // 传感器代表1个停车位
              }))
            }))
            .catch(error => {
              console.error('❌ Error fetching on-street data:', error)
              return { type: 'on-street', data: [] }
            })
        )

        // 等待所有数据加载完成
        const results = await Promise.all(promises)

        // 合并数据
        let allData = []
        results.forEach(result => {
          if (result.data && Array.isArray(result.data)) {
            allData = allData.concat(result.data)
          }
        })

        parkingData.value = allData

        console.log(`✅ Loaded ${parkingData.value.length} parking facilities`)
        console.log('📊 Off-street count:', results.find(r => r.type === 'off-street')?.data.length || 0)
        console.log('📊 On-street count:', results.find(r => r.type === 'on-street')?.data.length || 0)

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

      // 根据筛选条件过滤数据
      let filteredData = parkingData.value

      // 根据状态过滤
      if (statusFilter.value === 'on-street') {
        filteredData = parkingData.value.filter(parking =>
          parking.data_source === 'on-street' || parking.parking_type === 'On-Street'
        )
      } else if (statusFilter.value === 'off-street') {
        filteredData = parkingData.value.filter(parking =>
          parking.data_source === 'off-street' || parking.parking_type === 'Off-Street'
        )
      }

      console.log(`🗺️ 准备显示 ${filteredData.length} 个标记 (筛选类型: ${statusFilter.value})`)

      // 添加停车场针脚标记
      filteredData.forEach(parking => {
        if (parking.latitude && parking.longitude) {
          // 根据数据源设置不同的标记样式
          const spaces = parking.parking_spaces || 1
          let pinColor = '#28a745' // 默认绿色
          let pinIcon = '🅿️'

          if (parking.data_source === 'on-street' || parking.parking_type === 'On-Street') {
            // On-Street 传感器使用蓝色和车辆图标
            pinColor = '#007bff' // 蓝色
            pinIcon = '🚗'
          } else if (parking.data_source === 'off-street') {
            // Off-Street 停车场根据停车位数量设置颜色
            if (spaces > 500) {
              pinColor = '#dc3545' // 红色 - 大型停车场
            } else if (spaces > 100) {
              pinColor = '#fd7e14' // 橙色 - 中型停���场
            } else if (spaces > 50) {
              pinColor = '#ffc107' // 黄色 - 小型停车场
            }
            pinIcon = '🅿️'
            // 50以下保持绿色
          }

          // 创建自定义针脚图标
          const pinIconDiv = L.divIcon({
            html: `
              <div class="custom-pin" style="--pin-color: ${pinColor}">
                <div class="pin-head">
                  <div class="pin-content">
                    <span class="parking-icon">${pinIcon}</span>
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
            icon: pinIconDiv
          })

          // 创建详细的弹出窗口内容
          let displayAddress = parking.building_address || parking.device_id || '未知地址'
          let displayArea = parking.clue_small_area || parking.bay_id || '未知区域'
          let statusInfo = ''

          if (parking.status) {
            let statusText = parking.status
            if (parking.status === 'Unoccupied') statusText = '空闲'
            else if (parking.status === 'Present') statusText = '占用'

            statusInfo = `
              <div class="info-row">
                <span class="info-label">状态:</span>
                <span class="info-value">${statusText}</span>
              </div>
            `
          }

          const popupContent = `
            <div class="parking-popup">
              <div class="popup-body">
                <div class="popup-title">
                  ${parking.data_source === 'on-street' ? '路边停车传感器' : '停车场信息'}
                </div>

                <div class="info-row">
                  <span class="info-label">地址:</span>
                  <span class="info-value">${displayAddress}</span>
                </div>

                <div class="info-row">
                  <span class="info-label">类型:</span>
                  <span class="info-value">${parking.parking_type || '未知'}</span>
                </div>

                <div class="info-row">
                  <span class="info-label">区域:</span>
                  <span class="info-value">${displayArea}</span>
                </div>

                <div class="info-row">
                  <span class="info-label">停车位:</span>
                  <span class="info-value spaces-highlight">${spaces} 个</span>
                </div>

                ${statusInfo}

                <div class="popup-actions">
                  <button onclick="getDirections(${parking.latitude}, ${parking.longitude})" class="popup-btn">
                    导航
                  </button>
                </div>
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

      console.log(`🗺️ 成功添加 ${filteredData.length} 个标记到地图`)
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
    // 状态筛选功能 - 简化逻辑
    const setStatusFilter = (filter) => {
      statusFilter.value = filter
      console.log(`🔄 切换状态筛选到: ${filter}`)

      // 根据筛选类型决定API请求参数
      if (filter === 'on-street') {
        fetchParkingData({ type: 'on-street' })
      } else if (filter === 'off-street') {
        fetchParkingData({ type: 'off-street' })
      } else {
        fetchParkingData() // 显示所有类型
      }
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

/* 状态过滤按钮 */
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

/* 弹出窗口样式优化 - 全白色简洁设计 */
:deep(.custom-parking-popup .leaflet-popup-content-wrapper) {
  border-radius: 8px;
  padding: 0;
  overflow: hidden;
  background: white;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

:deep(.custom-parking-popup .leaflet-popup-content) {
  margin: 0;
  width: 250px !important;
}

:deep(.parking-popup) {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

:deep(.popup-title) {
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 1rem;
  text-align: center;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #eee;
}

:deep(.popup-body) {
  padding: 1.5rem;
  background: white;
}

:deep(.info-row) {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.8rem;
}

:deep(.info-row:last-of-type) {
  margin-bottom: 1.5rem;
}

:deep(.info-label) {
  font-weight: 500;
  color: #666;
  font-size: 0.9rem;
  flex-shrink: 0;
}

:deep(.info-value) {
  color: #333;
  font-size: 0.9rem;
  text-align: right;
  flex: 1;
  word-break: break-word;
  margin-left: 1rem;
}

:deep(.spaces-highlight) {
  color: #007bff;
  font-weight: bold;
  font-size: 1rem;
}

:deep(.popup-actions) {
  margin-top: 1rem;
}

:deep(.popup-btn) {
  width: 100%;
  padding: 0.8rem;
  border: 2px solid #007bff;
  border-radius: 6px;
  background: #007bff;
  color: white;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.9rem;
}

:deep(.popup-btn:hover) {
  background: #0056b3;
  border-color: #0056b3;
  transform: translateY(-1px);
}
</style>
