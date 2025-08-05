<template>
  <div class="home">
    <h1>欢迎来到 FIT5120 网页应用</h1>
    <p>这是一个使用 Vue.js + Flask + MySQL 构建的网页应用</p>

    <div class="api-test">
      <button @click="testAPI">测试后端连接</button>
      <div v-if="apiResponse" class="response">
        <h3>后端响应:</h3>
        <pre>{{ apiResponse }}</pre>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Home',
  data() {
    return {
      apiResponse: null
    }
  },
  methods: {
    async testAPI() {
      try {
        const response = await axios.get('/api/health')
        this.apiResponse = response.data
      } catch (error) {
        this.apiResponse = { error: '无法连接到后端' }
      }
    }
  }
}
</script>

<style scoped>
.home {
  text-align: center;
  max-width: 800px;
  margin: 0 auto;
}

h1 {
  color: #2c3e50;
  margin-bottom: 1rem;
}

.api-test {
  margin-top: 2rem;
}

button {
  background: #007bff;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background: #0056b3;
}

.response {
  margin-top: 1rem;
  text-align: left;
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
}
</style>
