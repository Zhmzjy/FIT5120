<template>
  <div class="parking-app">
    <!-- 顶部搜索栏 -->
    <div class="search-header">
      <div class="search-container">
        <div class="search-input-wrapper">
          <i class="search-icon">🔍</i>
          <input
            type="text"
            v-model="searchQuery"
            placeholder="Search Melbourne parking..."
            class="search-input"
            @input="onSearchInput"
          />
          <button v-if="searchQuery" @click="clearSearch" class="clear-btn">×</button>
        </div>
        <button @click="cancelSearch" class="cancel-btn">Cancel</button>
      </div>

      <!-- 过滤按钮 -->
      <div class="filter-buttons">
        <button
          v-for="filter in filterOptions"
          :key="filter.id"
          @click="toggleFilter(filter.id)"
          :class="['filter-btn', { active: activeFilters.includes(filter.id) }]"
        >
          {{ filter.label }}
          <span v-if="filter.hasDropdown" class="dropdown-arrow">▼</span>
        </button>
      </div>
    </div>

    <!-- 地图容器 -->
    <div class="map-container">
      <div id="melbourne-map" class="leaflet-map"></div>

      <!-- 实时数据状态指示器 -->
      <div class="realtime-status">
        <div :class="['status-dot', connectionStatus]"></div>
        <span class="status-text">
          {{ connectionStatus === 'connected' ? 'Live' :
             connectionStatus === 'connecting' ? 'Connecting...' : 'Offline' }}
        </span>
        <span v-if="lastUpdateTime" class="update-time">
          Updated {{ formatUpdateTime(lastUpdateTime) }}
        </span>
      </div>

      <!-- 实时控制按钮 -->
      <div class="realtime-controls">
        <button @click="manualRefresh" class="refresh-btn" :disabled="connectionStatus === 'connecting'">
          <i class="refresh-icon">🔄</i>
        </button>
        <button @click="simulateDataChange" class="demo-btn" title="Simulate data change">
          <i class="demo-icon">⚡</i>
        </button>
        <button @click="toggleRealTime" :class="['toggle-realtime-btn', { active: isRealTimeEnabled }]">
          {{ isRealTimeEnabled ? '📡' : '📴' }}
        </button>
      </div>

      <!-- 定位按钮 -->
      <button @click="centerToUserLocation" class="location-btn">
        <i class="location-icon">📍</i>
      </button>

      <!-- 路线规划按钮 -->
      <button @click="toggleRouting" class="routing-btn" :class="{ active: isRoutingMode }">
        <i class="routing-icon">🧭</i>
      </button>
    </div>

    <!-- 底部停车场列表 -->
    <div class="parking-list">
      <div class="list-header">
        <h3>{{ filteredParkingLots.length > 0 ? 'Nearby parking' : 'Search results' }}</h3>
        <button @click="sortParkingList" class="sort-btn">
          Sort by {{ currentSortBy }}
        </button>
      </div>

      <div class="parking-items">
        <div
          v-for="parking in displayedParkingLots"
          :key="parking.id"
          @click="selectParking(parking)"
          class="parking-item"
        >
          <div class="parking-main-info">
            <div class="parking-number">{{ parking.zoneNumber }}</div>
            <div class="parking-details">
              <h4 class="parking-name">{{ parking.name }}</h4>
              <div class="parking-meta">
                <span class="parking-spaces">{{ parking.available }}P</span>
                <span class="parking-price">${{ parking.price }}/Hr</span>
                <span class="parking-distance">{{ parking.distance }}m</span>
              </div>
            </div>
          </div>
          <div class="parking-status">
            <div :class="['status-indicator', parking.available > 10 ? 'available' : 'limited']"></div>
            <i class="chevron-right">›</i>
          </div>
        </div>
      </div>
    </div>

    <!-- 停车场详情弹窗 -->
    <div v-if="selectedParkingDetail" class="parking-detail-modal" @click="closeDetailModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ selectedParkingDetail.name }}</h3>
          <button @click="closeDetailModal" class="close-modal-btn">×</button>
        </div>

        <div class="modal-body">
          <div class="detail-row">
            <span class="label">Available Spaces:</span>
            <span class="value">{{ selectedParkingDetail.available }}/{{ selectedParkingDetail.total }}</span>
          </div>
          <div class="detail-row">
            <span class="label">Price:</span>
            <span class="value">${{ selectedParkingDetail.price }}/hour</span>
          </div>
          <div class="detail-row">
            <span class="label">Distance:</span>
            <span class="value">{{ selectedParkingDetail.distance }}m walk</span>
          </div>
          <div class="detail-row">
            <span class="label">Hours:</span>
            <span class="value">{{ selectedParkingDetail.hours }}</span>
          </div>

          <div class="action-buttons">
            <button @click="navigateToParking(selectedParkingDetail)" class="navigate-btn">
              Navigate
            </button>
            <button @click="reserveParking(selectedParkingDetail)" class="reserve-btn">
              Reserve
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, nextTick, onUnmounted } from 'vue'

export default {
  name: 'ProfessionalMelbourneMap',
  setup() {
    const searchQuery = ref('')
    const activeFilters = ref(['All Day'])
    const selectedParkingDetail = ref(null)
    const isRoutingMode = ref(false)
    const currentSortBy = ref('distance')
    const isRealTimeEnabled = ref(true)
    const lastUpdateTime = ref(null)
    const connectionStatus = ref('connecting') // connecting, connected, disconnected
    let map = null
    let markers = []
    let realTimeInterval = null

    // 过滤选项
    const filterOptions = [
      { id: 'now', label: 'Now', hasDropdown: false },
      { id: 'all-day', label: 'All Day', hasDropdown: true },
      { id: 'cost', label: 'Cost', hasDropdown: true },
      { id: 'availability', label: 'Availability', hasDropdown: true }
    ]

    // Melbourne停车场数据（模拟真实停车应用的数据结构）
    const parkingLots = ref([
      {
        id: 1,
        name: 'Collins Street Parking',
        zoneNumber: '33881262',
        coordinates: [-37.8136, 144.9631],
        available: 16,
        total: 200,
        price: 6.20,
        distance: 128,
        hours: '24 hours',
        type: 'paid',
        zone: 'CBD'
      },
      {
        id: 2,
        name: 'Flinders Station Parking',
        zoneNumber: '33881266',
        coordinates: [-37.8183, 144.9671],
        available: 8,
        total: 150,
        price: 5.50,
        distance: 132,
        hours: '6am-10pm',
        type: 'paid',
        zone: 'CBD'
      },
      {
        id: 3,
        name: 'Queen Victoria Market',
        zoneNumber: '33881260',
        coordinates: [-37.8076, 144.9568],
        available: 23,
        total: 300,
        price: 4.80,
        distance: 89,
        hours: '7am-6pm',
        type: 'paid',
        zone: 'CBD'
      },
      {
        id: 4,
        name: 'BOUNDARY STREET',
        zoneNumber: '33883210',
        coordinates: [-37.8316, 144.9581],
        available: 45,
        total: 60,
        price: 0,
        distance: 42,
        hours: 'Mon-Fri 9am-5pm',
        type: 'free',
        zone: 'South Melbourne'
      },
      {
        id: 5,
        name: 'MCG Sports Parking',
        zoneNumber: '33883208',
        coordinates: [-37.8200, 144.9834],
        available: 12,
        total: 500,
        price: 8.50,
        distance: 52,
        hours: 'Event days only',
        type: 'paid',
        zone: 'East Melbourne'
      },
      {
        id: 6,
        name: 'BOURKE STREET',
        zoneNumber: '33883206',
        coordinates: [-37.8139, 144.9651],
        available: 5,
        total: 40,
        price: 0,
        distance: 73,
        hours: '2hr limit',
        type: 'free',
        zone: 'CBD'
      }
    ])

    // 计算过滤后的停车场
    const filteredParkingLots = computed(() => {
      let filtered = parkingLots.value

      // 搜索过滤
      if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase()
        filtered = filtered.filter(parking =>
          parking.name.toLowerCase().includes(query) ||
          parking.zone.toLowerCase().includes(query) ||
          parking.zoneNumber.includes(query)
        )
      }

      // 其他过滤条件
      if (activeFilters.value.includes('availability')) {
        filtered = filtered.filter(parking => parking.available > 0)
      }

      return filtered
    })

    // 显示的停车场列表（排序后）
    const displayedParkingLots = computed(() => {
      const sorted = [...filteredParkingLots.value]

      switch (currentSortBy.value) {
        case 'distance':
          return sorted.sort((a, b) => a.distance - b.distance)
        case 'price':
          return sorted.sort((a, b) => a.price - b.price)
        case 'availability':
          return sorted.sort((a, b) => b.available - a.available)
        default:
          return sorted
      }
    })

    // 地图初始化
    const initMap = () => {
      try {
        if (typeof L !== 'undefined') {
          map = L.map('melbourne-map').setView([-37.8136, 144.9631], 15)

          L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
          }).addTo(map)

          addParkingMarkers()
        }
      } catch (error) {
        console.error('地图初始化失败:', error)
      }
    }

    // 添加停车场标记
    const addParkingMarkers = () => {
      markers = []

      parkingLots.value.forEach(parking => {
        // 创建自定义的蓝色P标记
        const customIcon = L.divIcon({
          className: 'custom-parking-marker',
          html: `
            <div class="parking-marker ${parking.available > 0 ? 'available' : 'full'}">
              <span class="parking-p">P</span>
              ${parking.available <= 5 && parking.available > 0 ? '<div class="low-spaces"></div>' : ''}
            </div>
          `,
          iconSize: [30, 30],
          iconAnchor: [15, 15]
        })

        const marker = L.marker(parking.coordinates, { icon: customIcon })
          .addTo(map)
          .bindPopup(`
            <div class="marker-popup">
              <h4>${parking.name}</h4>
              <p><strong>Zone:</strong> ${parking.zoneNumber}</p>
              <p><strong>Available:</strong> ${parking.available}/${parking.total}</p>
              <p><strong>Price:</strong> ${parking.price > 0 ? '$' + parking.price + '/hr' : 'Free'}</p>
              <button onclick="window.selectParkingFromMap(${parking.id})" class="popup-select-btn">
                Select
              </button>
            </div>
          `)

        marker.parkingId = parking.id
        markers.push(marker)
      })
    }

    // 实时数据功能
    const fetchRealTimeData = async () => {
      try {
        connectionStatus.value = 'connecting'
        const response = await fetch('/api/parking-lots/realtime')

        if (response.ok) {
          const data = await response.json()
          updateParkingData(data.parking_lots)
          lastUpdateTime.value = new Date(data.timestamp)
          connectionStatus.value = 'connected'
        } else {
          throw new Error('API response not ok')
        }
      } catch (error) {
        console.warn('实时数据获取失败，使用静态数据:', error)
        connectionStatus.value = 'disconnected'
        // 继续使用静态数据，不中断用户体验
      }
    }

    const updateParkingData = (newData) => {
      // 更新停车场数据
      newData.forEach(newLot => {
        const existingIndex = parkingLots.value.findIndex(lot => lot.id === newLot.id)
        if (existingIndex !== -1) {
          // 保持现有的 zoneNumber 和 distance 数据
          const existing = parkingLots.value[existingIndex]
          parkingLots.value[existingIndex] = {
            ...newLot,
            zoneNumber: existing.zoneNumber,
            distance: existing.distance
          }
        }
      })

      // 更新地图标记
      updateMapMarkers()
    }

    const updateMapMarkers = () => {
      if (!map || !markers.length) return

      markers.forEach(marker => {
        const parking = parkingLots.value.find(lot => lot.id === marker.parkingId)
        if (parking) {
          // 更新标记的弹窗内容
          marker.setPopupContent(`
            <div class="marker-popup">
              <h4>${parking.name}</h4>
              <p><strong>Zone:</strong> ${parking.zoneNumber || parking.id}</p>
              <p><strong>Available:</strong> <span class="${parking.available <= 5 ? 'low-availability' : ''}">${parking.available}/${parking.total}</span></p>
              <p><strong>Price:</strong> ${parking.price > 0 ? '$' + parking.price + '/hr' : 'Free'}</p>
              <p><strong>Updated:</strong> ${lastUpdateTime.value ? lastUpdateTime.value.toLocaleTimeString() : 'Just now'}</p>
              <button onclick="window.selectParkingFromMap(${parking.id})" class="popup-select-btn">
                Select
              </button>
            </div>
          `)

          // 更新标记样式
          const markerElement = marker.getElement()
          if (markerElement) {
            const parkingMarker = markerElement.querySelector('.parking-marker')
            if (parkingMarker) {
              parkingMarker.className = `parking-marker ${parking.available > 0 ? 'available' : 'full'}`
            }
          }
        }
      })
    }

    const startRealTimeUpdates = () => {
      if (realTimeInterval) return

      // 立即获取一次数据
      fetchRealTimeData()

      // 每30秒更新一次
      realTimeInterval = setInterval(() => {
        if (isRealTimeEnabled.value) {
          fetchRealTimeData()
        }
      }, 30000)
    }

    const stopRealTimeUpdates = () => {
      if (realTimeInterval) {
        clearInterval(realTimeInterval)
        realTimeInterval = null
      }
    }

    const toggleRealTime = () => {
      isRealTimeEnabled.value = !isRealTimeEnabled.value

      if (isRealTimeEnabled.value) {
        startRealTimeUpdates()
      } else {
        stopRealTimeUpdates()
        connectionStatus.value = 'disconnected'
      }
    }

    // 手动刷新数据
    const manualRefresh = () => {
      fetchRealTimeData()
    }

    // 模拟本地数据变化（用于演示）
    const simulateDataChange = () => {
      parkingLots.value.forEach(parking => {
        const change = Math.floor(Math.random() * 5) - 2 // -2 到 +2 的随机变化
        const newAvailable = Math.max(0, Math.min(parking.total, parking.available + change))
        parking.available = newAvailable
      })
      updateMapMarkers()
      lastUpdateTime.value = new Date()
    }

    // 格式化更新时间
    const formatUpdateTime = (date) => {
      if (!date) return ''
      const options = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }
      return new Intl.DateTimeFormat('en-AU', options).format(date)
    }

    // 事件处理函数
    const onSearchInput = () => {
      // 实时搜索逻辑
    }

    const clearSearch = () => {
      searchQuery.value = ''
    }

    const cancelSearch = () => {
      searchQuery.value = ''
    }

    const toggleFilter = (filterId) => {
      const index = activeFilters.value.indexOf(filterId)
      if (index > -1) {
        activeFilters.value.splice(index, 1)
      } else {
        activeFilters.value.push(filterId)
      }
    }

    const centerToUserLocation = () => {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition((position) => {
          const lat = position.coords.latitude
          const lng = position.coords.longitude
          map.setView([lat, lng], 16)
        })
      }
    }

    const toggleRouting = () => {
      isRoutingMode.value = !isRoutingMode.value
    }

    const sortParkingList = () => {
      const sortOptions = ['distance', 'price', 'availability']
      const currentIndex = sortOptions.indexOf(currentSortBy.value)
      currentSortBy.value = sortOptions[(currentIndex + 1) % sortOptions.length]
    }

    const selectParking = (parking) => {
      selectedParkingDetail.value = parking

      // 在地图上高亮选中的停车场
      if (map) {
        map.setView(parking.coordinates, 17)
        markers.forEach(marker => {
          if (marker.parkingId === parking.id) {
            marker.openPopup()
          }
        })
      }
    }

    const closeDetailModal = () => {
      selectedParkingDetail.value = null
    }

    const navigateToParking = (parking) => {
      const url = `https://www.google.com/maps/dir/?api=1&destination=${parking.coordinates[0]},${parking.coordinates[1]}`
      window.open(url, '_blank')
    }

    const reserveParking = (parking) => {
      alert(`Reserving parking at ${parking.name}`)
    }

    // 全局函数（供地图弹窗调用）
    window.selectParkingFromMap = (parkingId) => {
      const parking = parkingLots.value.find(p => p.id === parkingId)
      if (parking) {
        selectParking(parking)
      }
    }

    onMounted(async () => {
      await nextTick()
      setTimeout(() => {
        initMap()
        // 启动实时数据更新
        startRealTimeUpdates()
      }, 100)
    })

    onUnmounted(() => {
      stopRealTimeUpdates()
    })

    return {
      searchQuery,
      activeFilters,
      selectedParkingDetail,
      isRoutingMode,
      currentSortBy,
      filterOptions,
      filteredParkingLots,
      displayedParkingLots,
      onSearchInput,
      clearSearch,
      cancelSearch,
      toggleFilter,
      centerToUserLocation,
      toggleRouting,
      sortParkingList,
      selectParking,
      closeDetailModal,
      navigateToParking,
      reserveParking,
      isRealTimeEnabled,
      lastUpdateTime,
      connectionStatus,
      toggleRealTime,
      manualRefresh,
      simulateDataChange,
      formatUpdateTime
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
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* 搜索头部 */
.search-header {
  background: white;
  padding: 10px 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  z-index: 1000;
}

.search-container {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.search-input-wrapper {
  flex: 1;
  position: relative;
  background: #f0f0f0;
  border-radius: 25px;
  display: flex;
  align-items: center;
  padding: 8px 16px;
  margin-right: 12px;
}

.search-icon {
  margin-right: 8px;
  color: #666;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 16px;
  outline: none;
}

.search-input::placeholder {
  color: #999;
}

.clear-btn {
  background: none;
  border: none;
  font-size: 20px;
  color: #666;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
}

.cancel-btn {
  background: none;
  border: none;
  color: #007AFF;
  font-size: 16px;
  cursor: pointer;
  padding: 8px 12px;
}

/* 过滤按钮 */
.filter-buttons {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.filter-btn {
  background: #f0f0f0;
  border: none;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  color: #333;
  cursor: pointer;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s;
}

.filter-btn.active {
  background: #007AFF;
  color: white;
}

.dropdown-arrow {
  font-size: 10px;
}

/* 地图容器 */
.map-container {
  flex: 1;
  position: relative;
}

.leaflet-map {
  width: 100%;
  height: 100%;
}

.location-btn, .routing-btn {
  position: absolute;
  right: 16px;
  width: 44px;
  height: 44px;
  background: #007AFF;
  border: none;
  border-radius: 22px;
  color: white;
  font-size: 18px;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0,0,0,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.location-btn {
  bottom: 280px;
}

.routing-btn {
  bottom: 220px;
}

.routing-btn.active {
  background: #FF3B30;
}

/* 实时数据状态指示器 */
.realtime-status {
  position: absolute;
  top: 16px;
  left: 16px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 12px;
  padding: 8px 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 1000;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.status-dot.connecting {
  background: orange;
}

.status-dot.connected {
  background: green;
}

.status-dot.disconnected {
  background: red;
}

.status-text {
  font-size: 14px;
  color: #333;
}

.update-time {
  font-size: 12px;
  color: #666;
}

/* 实时控制按钮 */
.realtime-controls {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  gap: 8px;
  z-index: 1000;
}

.refresh-btn, .demo-btn, .toggle-realtime-btn {
  background: #007AFF;
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  cursor: pointer;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s;
}

.refresh-btn:disabled {
  background: #e0e0e0;
  cursor: not-allowed;
}

.toggle-realtime-btn.active {
  background: #FF3B30;
}

/* 停车场列表 */
.parking-list {
  background: white;
  border-radius: 16px 16px 0 0;
  max-height: 50vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.list-header {
  padding: 16px 20px 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f0f0f0;
}

.list-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.sort-btn {
  background: none;
  border: none;
  color: #007AFF;
  font-size: 14px;
  cursor: pointer;
}

.parking-items {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.parking-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.parking-item:hover {
  background: #f8f8f8;
}

.parking-main-info {
  display: flex;
  align-items: center;
  flex: 1;
}

.parking-number {
  background: #34C759;
  color: white;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
  margin-right: 12px;
  min-width: 60px;
  text-align: center;
}

.parking-details h4 {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: #333;
  font-weight: 600;
}

.parking-meta {
  display: flex;
  gap: 8px;
  font-size: 14px;
  color: #666;
}

.parking-spaces {
  font-weight: 600;
  color: #333;
}

.parking-price::before {
  content: '•';
  margin-right: 4px;
}

.parking-distance::before {
  content: '•';
  margin-right: 4px;
}

.parking-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-indicator.available {
  background: #34C759;
}

.status-indicator.limited {
  background: #FF9500;
}

.chevron-right {
  color: #C7C7CC;
  font-size: 16px;
}

/* 详情弹窗 */
.parking-detail-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal-content {
  background: white;
  border-radius: 16px;
  margin: 20px;
  max-width: 400px;
  width: 100%;
  overflow: hidden;
}

.modal-header {
  padding: 20px 20px 12px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.close-modal-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #666;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
}

.modal-body {
  padding: 20px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.label {
  color: #666;
  font-size: 14px;
}

.value {
  color: #333;
  font-size: 14px;
  font-weight: 600;
}

.action-buttons {
  margin-top: 24px;
  display: flex;
  gap: 12px;
}

.navigate-btn, .reserve-btn {
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.navigate-btn {
  background: #f0f0f0;
  color: #333;
}

.reserve-btn {
  background: #007AFF;
  color: white;
}

.navigate-btn:hover {
  background: #e0e0e0;
}

.reserve-btn:hover {
  background: #0056b3;
}

/* 自定义停车场标记样式 */
:global(.custom-parking-marker) {
  background: none !important;
  border: none !important;
}

:global(.parking-marker) {
  width: 30px;
  height: 30px;
  background: #007AFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: 0 2px 8px rgba(0,122,255,0.3);
}

:global(.parking-marker.full) {
  background: #FF3B30;
}

:global(.parking-p) {
  color: white;
  font-weight: bold;
  font-size: 14px;
}

:global(.low-spaces) {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 8px;
  height: 8px;
  background: #FF9500;
  border-radius: 50%;
  border: 2px solid white;
}

:global(.marker-popup) {
  text-align: center;
}

:global(.marker-popup h4) {
  margin: 0 0 8px 0;
  font-size: 14px;
}

:global(.marker-popup p) {
  margin: 4px 0;
  font-size: 12px;
}

:global(.popup-select-btn) {
  background: #007AFF;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  margin-top: 8px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .search-header {
    padding: 8px 12px;
  }

  .parking-list {
    max-height: 45vh;
  }

  .filter-buttons {
    gap: 6px;
  }

  .filter-btn {
    padding: 6px 12px;
    font-size: 13px;
  }
}
</style>
