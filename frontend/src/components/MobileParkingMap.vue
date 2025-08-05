<template>
  <div class="mobile-parking-app">
    <!-- 顶部状态栏模拟 -->
    <div class="status-bar">
      <div class="time">13:28</div>
      <div class="status-icons">
        <span class="signal">📶</span>
        <span class="wifi">📶</span>
        <span class="battery">🔋</span>
      </div>
    </div>

    <!-- 地图容器 - 全屏 -->
    <div class="map-container">
      <div id="melbourne-map" class="leaflet-map"></div>

      <!-- 用户位置按钮 -->
      <div class="user-location-btn">
        <i class="location-pin">📍</i>
      </div>

      <!-- 搜索按钮 -->
      <div class="search-btn">
        <i class="search-icon">🔍</i>
      </div>

      <!-- 导航按钮 -->
      <div class="navigation-btn">
        <i class="nav-arrow">🧭</i>
      </div>
    </div>

    <!-- 底部抽屉式面板 -->
    <div class="bottom-drawer" :class="{ expanded: isDrawerExpanded }">
      <!-- 拖拽手柄 -->
      <div class="drawer-handle" @click="toggleDrawer">
        <div class="handle-bar"></div>
      </div>

      <!-- 搜索输入框 -->
      <div class="search-section">
        <div class="search-input-container">
          <i class="input-icon">📍</i>
          <input
            type="text"
            v-model="searchQuery"
            placeholder="Enter Zone Number"
            class="zone-input"
            @input="onSearchInput"
          />
          <button v-if="searchQuery" @click="clearSearch" class="clear-input">×</button>
        </div>
      </div>

      <!-- 过滤器标签 -->
      <div class="filter-tabs">
        <button
          v-for="filter in filterOptions"
          :key="filter.id"
          @click="toggleFilter(filter.id)"
          :class="['filter-tab', { active: activeFilters.includes(filter.id) }]"
        >
          {{ filter.label }}
          <span v-if="filter.hasDropdown" class="dropdown-icon">▼</span>
        </button>
      </div>

      <!-- 结果标题 -->
      <div class="results-header">
        <h3>{{ searchQuery ? 'Search results' : 'Nearby parking' }}</h3>
      </div>

      <!-- 停车场列表 -->
      <div class="parking-results">
        <div
          v-for="parking in filteredParkingLots"
          :key="parking.id"
          @click="selectParking(parking)"
          class="parking-result-item"
        >
          <div class="zone-badge">{{ parking.zoneNumber }}</div>
          <div class="parking-info">
            <h4 class="parking-name">{{ parking.name }}</h4>
            <div class="parking-details">
              <span class="spaces">{{ parking.available }}P</span>
              <span class="price">${{ parking.price }}/Hr</span>
              <span class="distance">{{ parking.distance }}m</span>
            </div>
          </div>
          <div class="chevron">›</div>
        </div>
      </div>
    </div>

    <!-- 底部标签栏 -->
    <div class="bottom-tabs">
      <div class="tab-item active">
        <i class="tab-icon">📍</i>
        <span class="tab-label">Park</span>
      </div>
      <div class="tab-item">
        <i class="tab-icon">⏱️</i>
        <span class="tab-label">Sessions</span>
        <span class="notification-badge">3</span>
      </div>
      <div class="tab-item">
        <i class="tab-icon">📄</i>
        <span class="tab-label">Permits</span>
      </div>
      <div class="tab-item">
        <i class="tab-icon">👤</i>
        <span class="tab-label">Account</span>
      </div>
    </div>

    <!-- 停车场详情弹窗 -->
    <div v-if="selectedParkingDetail" class="parking-detail-overlay" @click="closeDetailModal">
      <div class="detail-modal" @click.stop>
        <div class="detail-header">
          <h3>{{ selectedParkingDetail.name }}</h3>
          <button @click="closeDetailModal" class="close-detail">×</button>
        </div>
        <div class="detail-content">
          <div class="detail-item">
            <span class="detail-label">Zone Number:</span>
            <span class="detail-value">{{ selectedParkingDetail.zoneNumber }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Available Spaces:</span>
            <span class="detail-value">{{ selectedParkingDetail.available }}/{{ selectedParkingDetail.total }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Rate:</span>
            <span class="detail-value">${{ selectedParkingDetail.price }}/hour</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Distance:</span>
            <span class="detail-value">{{ selectedParkingDetail.distance }}m walk</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Hours:</span>
            <span class="detail-value">{{ selectedParkingDetail.hours }}</span>
          </div>

          <div class="detail-actions">
            <button @click="navigateToParking(selectedParkingDetail)" class="action-btn secondary">
              Navigate
            </button>
            <button @click="startParking(selectedParkingDetail)" class="action-btn primary">
              Start Parking
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, nextTick } from 'vue'

export default {
  name: 'MobileParkingMap',
  setup() {
    const searchQuery = ref('')
    const activeFilters = ref(['All Day'])
    const selectedParkingDetail = ref(null)
    const isDrawerExpanded = ref(false)
    let map = null
    let userMarker = null

    // 过滤选项
    const filterOptions = [
      { id: 'now', label: 'Now', hasDropdown: false },
      { id: 'all-day', label: 'All Day', hasDropdown: true },
      { id: 'cost', label: 'Cost', hasDropdown: true },
      { id: 'availability', label: 'Availability', hasDropdown: true }
    ]

    // Melbourne停车场数据
    const parkingLots = ref([
      {
        id: 1,
        name: 'Palais Carpark',
        zoneNumber: '33881262',
        coordinates: [-37.8136, 144.9631],
        available: 16,
        total: 200,
        price: 6.20,
        distance: 128,
        hours: '24 hours',
        type: 'paid'
      },
      {
        id: 2,
        name: 'Palais Carpark',
        zoneNumber: '33881266',
        coordinates: [-37.8183, 144.9671],
        available: 16,
        total: 150,
        price: 5.50,
        distance: 132,
        hours: '6am-10pm',
        type: 'paid'
      },
      {
        id: 3,
        name: 'BOUNDARY STREET',
        zoneNumber: '33883210',
        coordinates: [-37.8076, 144.9568],
        available: 0,
        total: 60,
        price: 0,
        distance: 42,
        hours: 'Free Parking',
        type: 'free'
      },
      {
        id: 4,
        name: 'BOUNDARY STREET',
        zoneNumber: '33883208',
        coordinates: [-37.8316, 144.9581],
        available: 0,
        total: 80,
        price: 0,
        distance: 52,
        hours: 'Free Parking',
        type: 'free'
      },
      {
        id: 5,
        name: 'BOUNDARY STREET',
        zoneNumber: '33883206',
        coordinates: [-37.8200, 144.9834],
        available: 0,
        total: 40,
        price: 0,
        distance: 73,
        hours: 'Free Parking',
        type: 'free'
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
          parking.zoneNumber.includes(query)
        )
      }

      // 其他过滤条件
      if (activeFilters.value.includes('availability')) {
        filtered = filtered.filter(parking => parking.available > 0)
      }

      return filtered.sort((a, b) => a.distance - b.distance)
    })

    // 地图初始化 - 添加实时停车场标记和用户定位
    const initMap = () => {
      try {
        if (typeof L !== 'undefined') {
          // 使用墨尔本市中心的坐标
          map = L.map('melbourne-map', {
            zoomControl: false,
            attributionControl: false
          }).setView([-37.8136, 144.9631], 15)

          // 使用标准地图瓦片
          L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: ''
          }).addTo(map)

          // 自动添加所有停车场标记
          addAllParkingMarkers()

          // 获取用户位置
          getUserLocation()

          // 启动实时数据更新
          startRealTimeUpdates()
        }
      } catch (error) {
        console.error('地图初始化失败:', error)
      }
    }

    // 添加所有停车场标记到地图上
    const addAllParkingMarkers = () => {
      parkingLots.value.forEach(parking => {
        addParkingMarker(parking)
      })
    }

    // 添加单个停车场标记
    const addParkingMarker = (parking) => {
      const parkingIcon = L.divIcon({
        className: 'parking-marker-icon',
        html: `
          <div class="parking-marker ${parking.available > 0 ? 'available' : 'full'}">
            <span class="parking-p">P</span>
            ${parking.available <= 5 && parking.available > 0 ? '<div class="low-spaces-indicator"></div>' : ''}
            ${parking.type === 'free' ? '<div class="free-indicator">FREE</div>' : ''}
          </div>
        `,
        iconSize: [40, 40],
        iconAnchor: [20, 20]
      })

      const marker = L.marker(parking.coordinates, { icon: parkingIcon })
        .addTo(map)
        .on('click', () => {
          showParkingInfo(parking)
        })

      // 添加弹窗
      marker.bindPopup(`
        <div class="parking-popup">
          <h4>${parking.name}</h4>
          <p><strong>Zone:</strong> ${parking.zoneNumber}</p>
          <p><strong>Available:</strong> <span class="${parking.available <= 5 ? 'low-availability' : ''}">${parking.available}/${parking.total}</span></p>
          <p><strong>Rate:</strong> ${parking.price > 0 ? '$' + parking.price + '/hr' : 'Free Parking'}</p>
          <p><strong>Distance:</strong> ${parking.distance}m walk</p>
          <button onclick="window.selectParkingFromPopup(${parking.id})" class="popup-btn">View Details</button>
        </div>
      `)

      marker.parkingId = parking.id
      return marker
    }

    // 获取用户真实位置
    const getUserLocation = () => {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            const userLat = position.coords.latitude
            const userLng = position.coords.longitude

            // 添加用户位置标记
            const userIcon = L.divIcon({
              className: 'user-location-marker',
              html: `
                <div class="user-marker">
                  <div class="user-dot"></div>
                  <div class="user-pulse"></div>
                </div>
              `,
              iconSize: [24, 24],
              iconAnchor: [12, 12]
            })

            const userMarker = L.marker([userLat, userLng], { icon: userIcon })
              .addTo(map)
              .bindPopup(`
                <div class="user-popup">
                  <h4>您的位置</h4>
                  <p>Latitude: ${userLat.toFixed(6)}</p>
                  <p>Longitude: ${userLng.toFixed(6)}</p>
                  <button onclick="window.centerOnUser()" class="popup-btn">Center Map</button>
                </div>
              `)

            // 更新停车场距离
            updateParkingDistances(userLat, userLng)

            console.log('用户位置已获取:', userLat, userLng)
          },
          (error) => {
            console.warn('无法获取用户位置:', error.message)
            // 使用默认位置（墨尔本市中心）
            addDefaultUserLocation()
          },
          {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 300000
          }
        )
      } else {
        console.warn('浏览器不支持地理定位')
        addDefaultUserLocation()
      }
    }

    // 添加默认用户位置标记
    const addDefaultUserLocation = () => {
      const defaultLat = -37.8136
      const defaultLng = 144.9631

      const userIcon = L.divIcon({
        className: 'user-location-marker',
        html: `
          <div class="user-marker">
            <div class="user-dot"></div>
            <div class="user-pulse"></div>
          </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      })

      L.marker([defaultLat, defaultLng], { icon: userIcon })
        .addTo(map)
        .bindPopup(`
          <div class="user-popup">
            <h4>默认位置</h4>
            <p>墨尔本市中心</p>
            <p><small>无法获取您的实际位置</small></p>
          </div>
        `)
    }

    // 计算并更新停车场距离
    const updateParkingDistances = (userLat, userLng) => {
      parkingLots.value.forEach(parking => {
        const distance = calculateDistance(
          userLat, userLng,
          parking.coordinates[0], parking.coordinates[1]
        )
        parking.distance = Math.round(distance * 1000) // 转换为米
      })
    }

    // 计算两点间距离（公里）
    const calculateDistance = (lat1, lng1, lat2, lng2) => {
      const R = 6371 // 地球半径（公里）
      const dLat = (lat2 - lat1) * Math.PI / 180
      const dLng = (lng2 - lng1) * Math.PI / 180
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLng/2) * Math.sin(dLng/2)
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
      return R * c
    }

    // 显示停车场详细信息
    const showParkingInfo = (parking) => {
      selectedParkingDetail.value = parking

      // 高亮选中的停车场
      if (map) {
        map.setView(parking.coordinates, 17)
      }
    }

    // 实时数据更新
    const startRealTimeUpdates = () => {
      // 每30秒更新一次停车场数据
      setInterval(async () => {
        try {
          const response = await fetch('/api/parking-lots/realtime')
          if (response.ok) {
            const data = await response.json()
            updateRealTimeData(data.parking_lots)
          }
        } catch (error) {
          console.warn('实时数据更新失败:', error)
          // 模拟数据变化
          simulateDataUpdate()
        }
      }, 30000)
    }

    // 更新实时数据
    const updateRealTimeData = (newData) => {
      newData.forEach(newParking => {
        const existingIndex = parkingLots.value.findIndex(p => p.id === newParking.id)
        if (existingIndex !== -1) {
          // 保持现有的距离数据
          const existing = parkingLots.value[existingIndex]
          parkingLots.value[existingIndex] = {
            ...newParking,
            distance: existing.distance,
            zoneNumber: existing.zoneNumber
          }
        }
      })

      // 更新地图标记
      updateMapMarkers()
    }

    // 模拟数据更新（当API不可用时）
    const simulateDataUpdate = () => {
      parkingLots.value.forEach(parking => {
        const change = Math.floor(Math.random() * 5) - 2 // -2 到 +2 的随机变化
        parking.available = Math.max(0, Math.min(parking.total, parking.available + change))
      })
      updateMapMarkers()
    }

    // 更新地图上的标记
    const updateMapMarkers = () => {
      // 这里可以更新标记的样式和弹窗内容
      map.eachLayer(layer => {
        if (layer.options && layer.options.icon && layer.parkingId) {
          const parking = parkingLots.value.find(p => p.id === layer.parkingId)
          if (parking) {
            // 更新弹窗内容
            layer.setPopupContent(`
              <div class="parking-popup">
                <h4>${parking.name}</h4>
                <p><strong>Zone:</strong> ${parking.zoneNumber}</p>
                <p><strong>Available:</strong> <span class="${parking.available <= 5 ? 'low-availability' : ''}">${parking.available}/${parking.total}</span></p>
                <p><strong>Rate:</strong> ${parking.price > 0 ? '$' + parking.price + '/hr' : 'Free Parking'}</p>
                <p><strong>Distance:</strong> ${parking.distance}m walk</p>
                <button onclick="window.selectParkingFromPopup(${parking.id})" class="popup-btn">View Details</button>
              </div>
            `)
          }
        }
      })
    }

    // 全局函数
    window.selectParkingFromPopup = (parkingId) => {
      const parking = parkingLots.value.find(p => p.id === parkingId)
      if (parking) {
        showParkingInfo(parking)
      }
    }

    window.centerOnUser = () => {
      getUserLocation()
    }

    // 事件处理函数
    const toggleDrawer = () => {
      isDrawerExpanded.value = !isDrawerExpanded.value
    }

    const onSearchInput = () => {
      // 搜索逻辑
    }

    const clearSearch = () => {
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

    const closeDetailModal = () => {
      selectedParkingDetail.value = null
    }

    const navigateToParking = (parking) => {
      const url = `https://www.google.com/maps/dir/?api=1&destination=${parking.coordinates[0]},${parking.coordinates[1]}`
      window.open(url, '_blank')
    }

    const startParking = (parking) => {
      alert(`Starting parking session at ${parking.name}`)
    }

    onMounted(async () => {
      await nextTick()
      setTimeout(() => {
        initMap()
      }, 100)
    })

    return {
      searchQuery,
      activeFilters,
      selectedParkingDetail,
      isDrawerExpanded,
      filterOptions,
      filteredParkingLots,
      toggleDrawer,
      onSearchInput,
      clearSearch,
      toggleFilter,
      selectParking,
      closeDetailModal,
      navigateToParking,
      startParking
    }
  }
}
</script>

<style scoped>
.mobile-parking-app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #000;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif;
  position: relative;
  overflow: hidden;
}

/* 状态栏 */
.status-bar {
  height: 44px;
  background: rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  color: #333;
  font-size: 16px;
  font-weight: 600;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  backdrop-filter: blur(20px);
}

.time {
  font-weight: 700;
}

.status-icons {
  display: flex;
  gap: 4px;
}

/* 地图容器 */
.map-container {
  flex: 1;
  position: relative;
  margin-top: 44px;
}

.leaflet-map {
  width: 100%;
  height: 100%;
}

/* 地图上的按钮 */
.user-location-btn,
.search-btn,
.navigation-btn {
  position: absolute;
  width: 56px;
  height: 56px;
  background: #007AFF;
  border-radius: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(0, 122, 255, 0.3);
  cursor: pointer;
  z-index: 999;
}

.user-location-btn {
  bottom: 60px;
  left: 20px;
  background: #007AFF;
}

.search-btn {
  bottom: 130px;
  right: 20px;
}

.navigation-btn {
  bottom: 60px;
  right: 20px;
}

.user-location-btn i,
.search-btn i,
.navigation-btn i {
  font-size: 24px;
  color: white;
}

/* 底部抽屉 */
.bottom-drawer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  border-radius: 20px 20px 0 0;
  box-shadow: 0 -2px 20px rgba(0, 0, 0, 0.1);
  transform: translateY(calc(100% - 120px));
  transition: transform 0.3s ease;
  z-index: 1000;
  max-height: 80vh;
  overflow: hidden;
}

.bottom-drawer.expanded {
  transform: translateY(0);
}

.drawer-handle {
  padding: 12px 0;
  display: flex;
  justify-content: center;
  cursor: pointer;
}

.handle-bar {
  width: 40px;
  height: 4px;
  background: #C7C7CC;
  border-radius: 2px;
}

/* 搜索区域 */
.search-section {
  padding: 0 20px 16px;
}

.search-input-container {
  display: flex;
  align-items: center;
  background: #F2F2F7;
  border-radius: 25px;
  padding: 12px 16px;
  gap: 8px;
}

.input-icon {
  color: #8E8E93;
  font-size: 16px;
}

.zone-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 16px;
  outline: none;
  color: #333;
}

.zone-input::placeholder {
  color: #8E8E93;
}

.clear-input {
  background: none;
  border: none;
  color: #8E8E93;
  font-size: 18px;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
}

/* 过滤标签 */
.filter-tabs {
  display: flex;
  gap: 8px;
  padding: 0 20px 16px;
  overflow-x: auto;
}

.filter-tab {
  background: #F2F2F7;
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

.filter-tab.active {
  background: #007AFF;
  color: white;
}

.dropdown-icon {
  font-size: 10px;
}

/* 结果标题 */
.results-header {
  padding: 0 20px 12px;
  border-bottom: 1px solid #F2F2F7;
}

.results-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
  font-weight: 600;
}

/* 停车场结果列表 */
.parking-results {
  max-height: 300px;
  overflow-y: auto;
  padding-bottom: 80px;
}

.parking-result-item {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.parking-result-item:hover {
  background: #F8F8F8;
}

.zone-badge {
  background: #34C759;
  color: white;
  padding: 6px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 700;
  margin-right: 12px;
  min-width: 70px;
  text-align: center;
}

.parking-info {
  flex: 1;
}

.parking-name {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: #333;
  font-weight: 600;
}

.parking-details {
  display: flex;
  gap: 8px;
  font-size: 14px;
  color: #8E8E93;
}

.spaces {
  font-weight: 600;
  color: #333;
}

.price::before,
.distance::before {
  content: '•';
  margin-right: 4px;
}

.chevron {
  color: #C7C7CC;
  font-size: 18px;
}

/* 底部标签栏 */
.bottom-tabs {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 80px;
  background: white;
  border-top: 1px solid #F2F2F7;
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding-bottom: env(safe-area-inset-bottom);
  z-index: 1001;
}

.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  position: relative;
}

.tab-item.active .tab-icon {
  color: #007AFF;
}

.tab-item.active .tab-label {
  color: #007AFF;
}

.tab-icon {
  font-size: 24px;
  color: #8E8E93;
}

.tab-label {
  font-size: 12px;
  color: #8E8E93;
  font-weight: 500;
}

.notification-badge {
  position: absolute;
  top: -4px;
  right: -8px;
  background: #FF3B30;
  color: white;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 6px;
  min-width: 18px;
  text-align: center;
}

/* 详情弹窗 */
.parking-detail-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.detail-modal {
  background: white;
  border-radius: 16px;
  width: 100%;
  max-width: 400px;
  overflow: hidden;
}

.detail-header {
  padding: 20px;
  border-bottom: 1px solid #F2F2F7;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
  font-weight: 600;
}

.close-detail {
  background: none;
  border: none;
  font-size: 24px;
  color: #8E8E93;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
}

.detail-content {
  padding: 20px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.detail-label {
  color: #8E8E93;
  font-size: 14px;
}

.detail-value {
  color: #333;
  font-size: 14px;
  font-weight: 600;
}

.detail-actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
}

.action-btn {
  flex: 1;
  padding: 14px;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.secondary {
  background: #F2F2F7;
  color: #333;
}

.action-btn.primary {
  background: #007AFF;
  color: white;
}

.action-btn:hover {
  opacity: 0.8;
}

/* 自定义地图标记样式 */
:global(.user-location-marker) {
  background: none !important;
  border: none !important;
}

:global(.user-marker) {
  position: relative;
  width: 20px;
  height: 20px;
}

:global(.user-dot) {
  width: 12px;
  height: 12px;
  background: #007AFF;
  border: 3px solid white;
  border-radius: 50%;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
}

:global(.user-pulse) {
  width: 20px;
  height: 20px;
  background: rgba(0, 122, 255, 0.2);
  border-radius: 50%;
  position: absolute;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  100% {
    transform: scale(2);
    opacity: 0;
  }
}

:global(.selected-parking-marker) {
  background: none !important;
  border: none !important;
}

:global(.parking-pin) {
  position: relative;
}

:global(.pin-head) {
  width: 30px;
  height: 30px;
  background: #007AFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 700;
  font-size: 14px;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
}

:global(.pin-point) {
  position: absolute;
  bottom: -5px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 8px solid #007AFF;
}

/* 自定义停车场标记样式 */
:global(.parking-marker-icon) {
  background: none !important;
  border: none !important;
}

:global(.parking-marker) {
  width: 40px;
  height: 40px;
  background: #007AFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: 0 3px 12px rgba(0, 122, 255, 0.4);
  border: 3px solid white;
}

:global(.parking-marker.full) {
  background: #FF3B30;
  box-shadow: 0 3px 12px rgba(255, 59, 48, 0.4);
}

:global(.parking-marker.available) {
  background: #007AFF;
  box-shadow: 0 3px 12px rgba(0, 122, 255, 0.4);
}

:global(.parking-p) {
  color: white;
  font-weight: 700;
  font-size: 16px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

:global(.low-spaces-indicator) {
  position: absolute;
  top: -3px;
  right: -3px;
  width: 12px;
  height: 12px;
  background: #FF9500;
  border-radius: 50%;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}

:global(.free-indicator) {
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  background: #34C759;
  color: white;
  font-size: 8px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 6px;
  white-space: nowrap;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

:global(.parking-popup) {
  text-align: center;
  min-width: 200px;
}

:global(.parking-popup h4) {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #333;
  font-weight: 600;
}

:global(.parking-popup p) {
  margin: 4px 0;
  font-size: 13px;
  color: #666;
}

:global(.parking-popup .low-availability) {
  color: #FF9500;
  font-weight: 600;
}

:global(.popup-btn) {
  background: #007AFF;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 8px;
  transition: all 0.2s;
}

:global(.popup-btn:hover) {
  background: #0056b3;
}

:global(.user-popup) {
  text-align: center;
  min-width: 180px;
}

:global(.user-popup h4) {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #333;
  font-weight: 600;
}

:global(.user-popup p) {
  margin: 4px 0;
  font-size: 12px;
  color: #666;
}

:global(.user-popup small) {
  color: #999;
  font-style: italic;
}

/* 响应式设计 */
@media (max-width: 375px) {
  .search-section {
    padding: 0 16px 12px;
  }

  .filter-tabs {
    padding: 0 16px 12px;
  }

  .results-header {
    padding: 0 16px 8px;
  }

  .parking-result-item {
    padding: 12px 16px;
  }
}
</style>
