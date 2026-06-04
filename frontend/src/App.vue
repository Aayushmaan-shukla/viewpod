<template>
  <div class="app-container">
    <aside class="sidebar glass-panel">
      <div class="sidebar-header">
        <div class="logo">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-box"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
          <h1>PodViewer</h1>
        </div>
        <div class="status-indicator">
          <span class="dot" :class="{ 'connected': isConnected }"></span>
          {{ isConnected ? 'Connected' : 'Reconnecting...' }}
        </div>
      </div>
      
      <div class="search-bar">
        <input type="text" v-model="searchQuery" placeholder="Search pods..." />
      </div>

      <div class="pod-list">
        <div 
          v-for="pod in filteredPods" 
          :key="pod.name"
          class="pod-item animate-fade-in"
          :class="{ active: selectedPod?.name === pod.name }"
          @click="selectPod(pod)"
        >
          <div class="pod-status" :class="pod.status.toLowerCase()"></div>
          <div class="pod-info">
            <span class="pod-name">{{ pod.name }}</span>
            <span class="pod-namespace">{{ pod.namespace }}</span>
          </div>
        </div>
        <div v-if="filteredPods.length === 0" class="no-pods">
          No pods found.
        </div>
      </div>
    </aside>

    <main class="main-content">
      <LogViewer v-if="selectedPod" :pod="selectedPod" />
      <div v-else class="empty-state animate-fade-in">
        <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" class="feather feather-terminal"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
        <h2>Select a pod to view logs</h2>
        <p>Real-time Kubernetes log streaming</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import LogViewer from './components/LogViewer.vue';

const pods = ref([]);
const selectedPod = ref(null);
const searchQuery = ref('');
const isConnected = ref(false);
let eventSource = null;

const filteredPods = computed(() => {
  if (!searchQuery.value) return pods.value;
  const q = searchQuery.value.toLowerCase();
  return pods.value.filter(p => p.name.toLowerCase().includes(q) || p.namespace.toLowerCase().includes(q));
});

const selectPod = (pod) => {
  selectedPod.value = pod;
};

const fetchInitialPods = async () => {
  try {
    const res = await fetch('http://localhost:8000/api/pods');
    if (res.ok) {
      pods.value = await res.json();
    }
  } catch (error) {
    console.error('Failed to fetch initial pods:', error);
  }
};

const setupSSE = () => {
  eventSource = new EventSource('http://localhost:8000/api/events');
  
  eventSource.onopen = () => {
    isConnected.value = true;
  };

  eventSource.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      const action = payload.event;
      const podData = JSON.parse(payload.data);

      if (action === 'ADDED' || action === 'MODIFIED') {
        const index = pods.value.findIndex(p => p.name === podData.name && p.namespace === podData.namespace);
        if (index > -1) {
          pods.value[index] = podData;
        } else {
          pods.value.unshift(podData);
        }
      } else if (action === 'DELETED') {
        pods.value = pods.value.filter(p => !(p.name === podData.name && p.namespace === podData.namespace));
        
        // Auto-reconnect logic if the selected pod is deleted and a replacement spins up
        if (selectedPod.value && selectedPod.value.name === podData.name) {
          // Look for a replacement pod with the same labels
          const parentLabels = podData.labels['app'] || podData.labels['app.kubernetes.io/name'];
          if (parentLabels) {
            setTimeout(() => {
              const replacement = pods.value.find(p => (p.labels['app'] === parentLabels || p.labels['app.kubernetes.io/name'] === parentLabels) && p.status === 'Running');
              if (replacement) {
                selectPod(replacement);
              }
            }, 1000);
          }
        }
      }
    } catch (e) {
      console.error('Error parsing SSE event:', e);
    }
  };

  eventSource.onerror = () => {
    isConnected.value = false;
    eventSource.close();
    // Try reconnecting after 3 seconds
    setTimeout(setupSSE, 3000);
  };
};

onMounted(() => {
  fetchInitialPods();
  setupSSE();
});

onUnmounted(() => {
  if (eventSource) {
    eventSource.close();
  }
});
</script>

<style scoped>
.app-container {
  display: flex;
  width: 100%;
  height: 100%;
}

.sidebar {
  width: 320px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar-header {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-bottom: 1px solid var(--panel-border);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--accent-color);
}

.logo h1 {
  font-size: 1.25rem;
  letter-spacing: -0.025em;
  color: var(--text-primary);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--danger);
  box-shadow: 0 0 8px var(--danger);
}

.dot.connected {
  background-color: var(--success);
  box-shadow: 0 0 8px var(--success);
}

.search-bar {
  padding: 16px;
  border-bottom: 1px solid var(--panel-border);
}

.search-bar input {
  width: 100%;
  padding: 10px 14px;
  border-radius: 6px;
  border: 1px solid var(--panel-border);
  background: rgba(0, 0, 0, 0.2);
  color: var(--text-primary);
  font-size: 0.875rem;
  outline: none;
  transition: all 0.2s;
}

.search-bar input:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
}

.pod-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pod-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.pod-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.pod-item.active {
  background: rgba(56, 189, 248, 0.1);
  border-color: rgba(56, 189, 248, 0.3);
}

.pod-status {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--text-secondary);
}

.pod-status.running { background: var(--success); }
.pod-status.pending { background: var(--warning); }
.pod-status.failed { background: var(--danger); }
.pod-status.error { background: var(--danger); }

.pod-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.pod-name {
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pod-namespace {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.no-pods {
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.875rem;
  padding: 24px;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
  background: rgba(0, 0, 0, 0.3);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-secondary);
  gap: 16px;
}

.empty-state svg {
  opacity: 0.5;
}

.empty-state h2 {
  font-size: 1.25rem;
  color: var(--text-primary);
}
</style>
