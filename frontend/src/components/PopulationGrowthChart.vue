<template>
  <div class="population-growth-chart">
    <h2 style="text-align:center;">Melbourne CBD Population Growth Trend</h2>
    <div ref="chartRef" class="chart-container"></div>
    <div v-if="loading" class="loading-text">Loading chart...</div>
    <div v-if="error" class="error-text">Failed to load data: {{ error }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'

// 图表容器 DOM 引用
const chartRef = ref(null)
let chartInstance = null

// 响应式状态
const years = ref([])
const populations = ref([])
const loading = ref(true)
const error = ref(null)

// 渲染图表
function renderChart() {
  if (!chartInstance) return

  chartInstance.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: years.value,
      name: 'Year',
      axisLine: { lineStyle: { color: '#888' } }
    },
    yAxis: {
      type: 'value',
      name: 'Population',
      axisLine: { lineStyle: { color: '#888' } }
    },
    series: [
      {
        name: 'CBD Population',
        type: 'line',
        smooth: true,
        data: populations.value,
        symbol: 'circle',
        symbolSize: 9,
        lineStyle: { width: 4 }
      }
    ],
    grid: { left: 40, right: 20, top: 50, bottom: 40 }
  })
}

// 获取后端数据 + 初始化图表
onMounted(async () => {
  chartInstance = echarts.init(chartRef.value)

  try {
    // ⚠️ 这里的 API 要和你后端人口数据接口匹配
    const res = await axios.get('/api/population/trend')
    if (res.data.success) {
      years.value = res.data.years
      populations.value = res.data.counts
      renderChart()
    } else {
      error.value = res.data.error || 'Data fetch failed.'
    }
  } catch (err) {
    error.value = err.message || 'Network error'
  } finally {
    loading.value = false
  }

  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  if (chartInstance) chartInstance.dispose()
})

function resizeChart() {
  if (chartInstance) chartInstance.resize()
}
</script>

<style scoped>
.population-growth-chart {
  width: 100%;
  height: 100%;
  padding: 0;
  position: relative;
}
.chart-container {
  width: 600px;
  max-width: 90vw;
  height: 360px;
  margin: 0 auto;
}
.loading-text, .error-text {
  text-align: center;
  color: #999;
  margin-top: 20px;
}
.error-text {
  color: red;
}
</style>



