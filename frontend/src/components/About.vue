<template>
  <div class="about">
    <h1>About Project</h1>
    <div class="content">
      <h2>Technology Stack</h2>
      <div class="tech-stack">
        <div class="tech-category">
          <h3>Frontend</h3>
          <ul>
            <li>Vue.js 3</li>
            <li>Vue Router</li>
            <li>Axios</li>
            <li>Leaflet Map</li>
          </ul>
        </div>
        <div class="tech-category">
          <h3>Backend</h3>
          <ul>
            <li>Flask</li>
            <li>SQLAlchemy</li>
            <li>MySQL</li>
            <li>RESTful API</li>
          </ul>
        </div>
        <div class="tech-category">
          <h3>Database</h3>
          <ul>
            <li>MySQL</li>
            <li>Real-time updates</li>
            <li>Data persistence</li>
          </ul>
        </div>
        <div class="tech-category">
          <h3>Deployment</h3>
          <ul>
            <li>Docker</li>
            <li>Docker Compose</li>
            <li>Container orchestration</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'About'
}
</script>

<style scoped>
.about {
  padding: 2rem;
  max-width: 800px;
  margin: 0 auto;
}

h1 {
  color: #2c3e50;
  margin-bottom: 2rem;
}

.tech-stack {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 2rem;
  margin-top: 1rem;
}

.tech-category {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
}

.tech-category h3 {
  color: #3498db;
  margin-bottom: 1rem;
}

.tech-category ul {
  list-style: none;
  padding: 0;
}

.tech-category li {
  padding: 0.25rem 0;
  color: #666;
}
</style>
