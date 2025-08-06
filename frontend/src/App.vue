<template>
  <div id="app">
    <MelbourneParkingMap />
  </div>
</template>

<script>
import MelbourneParkingMap from './components/MelbourneParkingMap.vue'

export default {
  name: 'App',
  components: {
    MelbourneParkingMap
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

body, html {
  height: 100%;
  margin: 0;
  padding: 0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
</style>
