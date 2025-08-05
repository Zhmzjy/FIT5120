<template>
  <div class="melbourne-parking-app">
    <!-- Header Section -->
    <header class="app-header">
      <div class="header-content">
        <h1 class="app-title">
          <span class="title-icon">🅿️</span>
          Melbourne Live Parking
        </h1>
        <p class="app-subtitle">Find real-time parking spaces across Melbourne CBD</p>
      </div>
    </header>

    <!-- Search Section -->
    <div class="search-section">
      <div class="search-container">
        <div class="search-input-group">
          <input
            v-model="searchQuery"
            @keyup.enter="performSearch"
            type="text"
            placeholder="Enter postcode or suburb (e.g., 3000, Melbourne CBD)"
            class="search-input"
          >
          <button @click="performSearch" class="search-btn" :disabled="isSearching">
            {{ isSearching ? '🔍' : '🔍' }}
          </button>
        </div>
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
        </div>
      </div>
    </div>

    <!-- Stats Bar -->
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
        <span class="stat-label">Occupancy</span>
      </div>
    </div>

    <!-- Map Container -->
    <div class="map-section">
      <div id="map" class="parking-map"></div>

      <!-- Map Controls -->
      <div class="map-controls">
        <button @click="refreshData" class="control-btn refresh" :disabled="isLoading">
          <span class="btn-icon">🔄</span>
          {{ isLoading ? 'Updating...' : 'Refresh' }}
        </button>
        <button @click="locateUser" class="control-btn locate">
          <span class="btn-icon">📍</span>
          My Location
        </button>
      </div>

      <!-- Loading Overlay -->
      <div v-if="isLoading" class="loading-overlay">
        <div class="loading-spinner"></div>
        <p class="loading-text">{{ loadingMessage }}</p>
      </div>
    </div>

    <!-- Parking Details Panel -->
    <div v-if="selectedParking" class="details-panel" :class="{ visible: selectedParking }">
      <div class="panel-header">
        <h3 class="panel-title">
          {{ selectedParking.kerbside_id ? `Space ${selectedParking.kerbside_id}` : selectedParking.name }}
        </h3>
        <button @click="closePanel" class="close-btn">✕</button>
      </div>

      <div class="panel-content">
        <div class="status-indicator" :class="getStatusClass(selectedParking)">
          <span class="status-dot"></span>
          <span class="status-text">{{ getStatusText(selectedParking) }}</span>
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

          <div class="detail-item" v-if="selectedParking.status_timestamp">
            <span class="detail-label">Last Update</span>
            <span class="detail-value">{{ formatTimestamp(selectedParking.status_timestamp) }}</span>
          </div>
        </div>

        <div class="action-buttons">
          <button @click="getDirections" class="action-btn primary">
            <span class="btn-icon">🧭</span>
            Get Directions
          </button>
          <button @click="shareLocation" class="action-btn secondary">
            <span class="btn-icon">📤</span>
            Share
          </button>
        </div>
      </div>
    </div>

    <!-- Status Message -->
    <div v-if="statusMessage" class="status-message" :class="messageType">
      {{ statusMessage }}
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, onUnmounted, watch } from 'vue'
import axios from 'axios'

export default {
  name: 'SimpleMelbourneMap',
  setup() {
    // Reactive data
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

    // Map variables
    let map = null
    let markersLayer = null
    let userMarker = null
    let refreshInterval = null

    // API Base URL
    const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://localhost:5001'

    // Initialize map
    const initMap = async () => {
      try {
        if (typeof window.L === 'undefined') {
          throw new Error('Leaflet library not loaded')
        }

        // Create map centered on Melbourne CBD
        map = window.L.map('map', {
          center: [-37.8136, 144.9631],
          zoom: 14,
          zoomControl: true,
          attributionControl: true
        })

        // Add tile layer with modern style
        window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors',
          maxZoom: 19
        }).addTo(map)

        // Create marker layer
        markersLayer = window.L.layerGroup().addTo(map)

        console.log('Map initialized successfully')

        // Load initial data
        await Promise.all([
          fetchParkingData(),
          fetchParkingStats()
        ])

      } catch (error) {
        console.error('Map initialization failed:', error)
        showMessage('Failed to initialize map', 'error')
      }
    }

    // Fetch real-time parking data
    const fetchParkingData = async (searchParams = {}) => {
      try {
        isLoading.value = true
        loadingMessage.value = 'Fetching real-time parking data...'

        const params = {
          status: statusFilter.value,
          ...searchParams
        }

        const response = await axios.get(`${API_BASE}/api/parking/live`, {
          params,
          timeout: 15000
        })

        if (response.data.success) {
          parkingData.value = response.data.data
          updateMapMarkers()
          showMessage(`Found ${response.data.count} parking spaces`, 'success')
        } else {
          throw new Error(response.data.error || 'Failed to fetch parking data')
        }

      } catch (error) {
        console.error('Error fetching parking data:', error)
        showMessage('Unable to fetch real-time data. Please try again.', 'error')

        // Fallback to demo data
        parkingData.value = getDemoData()
        updateMapMarkers()

      } finally {
        isLoading.value = false
      }
    }

    // Fetch parking statistics
    const fetchParkingStats = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/stats`)
        if (response.data.success) {
          parkingStats.value = response.data.stats
        }
      } catch (error) {
        console.error('Error fetching stats:', error)
      }
    }

    // Update map markers
    const updateMapMarkers = () => {
      if (!markersLayer || !map) return

      // Clear existing markers
      markersLayer.clearLayers()

      // Add parking markers
      parkingData.value.forEach(parking => {
        const [lat, lng] = parking.coordinates

        // Create custom icon based on status
        const isAvailable = parking.status === 'Unoccupied'
        const iconColor = isAvailable ? '#22c55e' : '#ef4444'

        const customIcon = window.L.divIcon({
          html: `<div class="custom-marker ${isAvailable ? 'available' : 'occupied'}">
                   <span class="marker-icon">${isAvailable ? '🅿️' : '🚫'}</span>
                 </div>`,
          className: 'custom-marker-container',
          iconSize: [30, 30],
          iconAnchor: [15, 15]
        })

        const marker = window.L.marker([lat, lng], { icon: customIcon })
          .addTo(markersLayer)
          .on('click', () => selectParking(parking))

        // Add popup
        const popupContent = `
          <div class="marker-popup">
            <strong>Space ${parking.kerbside_id || parking.id}</strong><br>
            Status: <span class="${isAvailable ? 'available' : 'occupied'}">${parking.status}</span><br>
            ${parking.zone_number ? `Zone: ${parking.zone_number}` : ''}
          </div>
        `
        marker.bindPopup(popupContent)
      })
    }

    // Search functionality
    const performSearch = async () => {
      if (!searchQuery.value.trim()) {
        showMessage('Please enter a search term', 'warning')
        return
      }

      try {
        isSearching.value = true
        loadingMessage.value = 'Searching parking near your location...'

        const response = await axios.get(`${API_BASE}/api/parking/search`, {
          params: { q: searchQuery.value.trim() }
        })

        if (response.data.success) {
          parkingData.value = response.data.data

          // Center map on search results
          if (response.data.center) {
            map.setView(response.data.center, 15)
          }

          updateMapMarkers()
          showMessage(`Found ${response.data.count} parking spaces near "${response.data.query}"`, 'success')
        }

      } catch (error) {
        console.error('Search error:', error)
        showMessage('Search failed. Please try again.', 'error')
      } finally {
        isSearching.value = false
      }
    }

    // Filter functions
    const setStatusFilter = (filter) => {
      statusFilter.value = filter
      fetchParkingData()
    }

    // Utility functions
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

            // Add user marker
            if (userMarker) {
              map.removeLayer(userMarker)
            }

            userMarker = window.L.marker([latitude, longitude], {
              icon: window.L.divIcon({
                html: '<div class="user-marker">📍</div>',
                className: 'user-marker-container',
                iconSize: [20, 20]
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
          title: 'Parking Space',
          text: `Found a parking space: ${selectedParking.value.kerbside_id}`,
          url: window.location.href
        })
      }
    }

    const getStatusClass = (parking) => {
      return parking.status === 'Unoccupied' ? 'available' : 'occupied'
    }

    const getStatusText = (parking) => {
      return parking.status === 'Unoccupied' ? 'Available' : 'Occupied'
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
        status_timestamp: new Date().toISOString()
      }
    ]

    // Lifecycle hooks
    onMounted(() => {
      initMap()

      // Set up auto-refresh
      refreshInterval = setInterval(() => {
        fetchParkingData()
      }, 60000) // Refresh every minute
    })

    onUnmounted(() => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
    })

    return {
      // Data
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

      // Methods
      performSearch,
      setStatusFilter,
      selectParking,
      closePanel,
      refreshData,
      locateUser,
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
/* Modern Melbourne Parking App Styles */
.melbourne-parking-app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* Header */
.app-header {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 1rem 2rem;
  box-shadow: 0 2px 20px rgba(0,0,0,0.1);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
}

.app-title {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 700;
  color: #1a202c;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.title-icon {
  font-size: 2rem;
}

.app-subtitle {
  margin: 0.25rem 0 0;
  color: #64748b;
  font-size: 0.95rem;
}

/* Search Section */
.search-section {
  background: white;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e2e8f0;
}

.search-container {
  max-width: 1200px;
  margin: 0 auto;
}

.search-input-group {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.search-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.search-btn {
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.search-btn:hover {
  background: #2563eb;
}

.filter-buttons {
  display: flex;
  gap: 0.5rem;
}

.filter-btn {
  padding: 0.5rem 1rem;
  border: 2px solid #e2e8f0;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.9rem;
  font-weight: 500;
}

.filter-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

/* Stats Bar */
.stats-bar {
  background: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: center;
  gap: 2rem;
  border-bottom: 1px solid #e2e8f0;
}

.stat-item {
  text-align: center;
}

.stat-number {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a202c;
}

.stat-label {
  font-size: 0.8rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-item.available .stat-number {
  color: #22c55e;
}

.stat-item.occupied .stat-number {
  color: #ef4444;
}

/* Map Section */
.map-section {
  flex: 1;
  position: relative;
  background: #f8fafc;
}

.parking-map {
  width: 100%;
  height: 100%;
}

/* Map Controls */
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
  padding: 0.75rem 1rem;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}

.control-btn:hover {
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  transform: translateY(-1px);
}

.control-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Details Panel */
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
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1a202c;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #64748b;
  padding: 0;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.close-btn:hover {
  background: #f1f5f9;
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
}

.status-indicator.available {
  background: #dcfce7;
  color: #166534;
}

.status-indicator.occupied {
  background: #fee2e2;
  color: #991b1b;
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
  color: #64748b;
}

.detail-value {
  color: #1a202c;
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
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.action-btn.primary {
  background: #3b82f6;
  color: white;
}

.action-btn.primary:hover {
  background: #2563eb;
}

.action-btn.secondary {
  background: #f1f5f9;
  color: #475569;
}

.action-btn.secondary:hover {
  background: #e2e8f0;
}

/* Loading Overlay */
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
  border: 4px solid #e2e8f0;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-text {
  margin-top: 1rem;
  color: #64748b;
  font-weight: 500;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Status Message */
.status-message {
  position: fixed;
  top: 1rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 500;
  z-index: 3000;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}

.status-message.success {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #bbf7d0;
}

.status-message.error {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.status-message.warning {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fde68a;
}

.status-message.info {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #bfdbfe;
}

/* Custom Map Markers */
:deep(.custom-marker-container) {
  background: none !important;
  border: none !important;
}

:deep(.custom-marker) {
  background: white;
  border-radius: 50%;
  box-shadow: 0 2px 10px rgba(0,0,0,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  font-size: 16px;
}

:deep(.custom-marker.available) {
  border: 2px solid #22c55e;
}

:deep(.custom-marker.occupied) {
  border: 2px solid #ef4444;
}

:deep(.user-marker-container) {
  background: none !important;
  border: none !important;
}

:deep(.user-marker) {
  font-size: 20px;
  text-shadow: 0 0 3px rgba(0,0,0,0.5);
}

/* Responsive Design */
@media (max-width: 768px) {
  .app-header {
    padding: 1rem;
  }

  .search-section {
    padding: 1rem;
  }

  .stats-bar {
    padding: 1rem;
    gap: 1rem;
  }

  .filter-buttons {
    flex-wrap: wrap;
  }

  .details-panel {
    max-height: 60vh;
  }

  .action-buttons {
    flex-direction: column;
  }
}

/* Popup Styles */
:deep(.leaflet-popup-content) {
  margin: 8px 12px;
  line-height: 1.4;
}

:deep(.marker-popup) {
  text-align: center;
}

:deep(.marker-popup .available) {
  color: #22c55e;
  font-weight: bold;
}

:deep(.marker-popup .occupied) {
  color: #ef4444;
  font-weight: bold;
}
</style>
