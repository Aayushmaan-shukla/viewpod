<template>
  <div class="log-viewer">
    <div class="log-header glass-panel">
      <div class="header-info">
        <h2>{{ pod.name }}</h2>
        <span class="namespace-badge">{{ pod.namespace }}</span>
      </div>
      <div class="header-actions">
        <!-- Container selector if multiple exist -->
        <select v-if="pod.containers && pod.containers.length > 1" v-model="selectedContainer" class="container-select">
          <option v-for="c in pod.containers" :key="c" :value="c">{{ c }}</option>
        </select>
        <button class="action-btn" @click="clearLogs" title="Clear logs">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
        </button>
        <button class="action-btn" @click="scrollToBottom" title="Scroll to bottom" :class="{ 'active-follow': autoScroll }">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><polyline points="19 12 12 19 5 12"></polyline></svg>
        </button>
      </div>
    </div>
    
    <div class="log-stream-container" ref="logContainer" @scroll="handleScroll">
      <div class="log-lines">
        <div v-for="(line, index) in logs" :key="index" class="log-line">
          {{ line }}
        </div>
      </div>
      <div v-if="logs.length === 0 && !error" class="loading-logs">
        Waiting for logs...
      </div>
      <div v-if="error" class="error-msg">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue';

const props = defineProps({
  pod: {
    type: Object,
    required: true
  }
});

const logs = ref([]);
const error = ref('');
const logContainer = ref(null);
const autoScroll = ref(true);
const selectedContainer = ref(null);
let abortController = null;

const startLogStream = async () => {
  // Reset state
  logs.value = [];
  error.value = '';
  
  if (abortController) {
    abortController.abort();
  }
  
  abortController = new AbortController();
  
  let url = `http://localhost:8000/api/logs/${props.pod.namespace}/${props.pod.name}`;
  if (selectedContainer.value) {
    url += `?container=${selectedContainer.value}`;
  }

  try {
    const response = await fetch(url, { signal: abortController.signal });
    
    if (!response.ok) {
      error.value = `Failed to stream logs: ${response.statusText}`;
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');
      
      // Handle partial lines
      for (let i = 0; i < lines.length - 1; i++) {
        if (lines[i].trim() !== '') {
          logs.value.push(lines[i]);
        }
      }
      // If the last line doesn't end with a newline, we technically should buffer it,
      // but for simplicity we push it if it's not empty.
      if (lines[lines.length - 1].trim() !== '') {
        logs.value.push(lines[lines.length - 1]);
      }

      if (autoScroll.value) {
        nextTick(scrollToBottom);
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError') {
      error.value = `Stream closed or error: ${e.message}`;
    }
  }
};

const scrollToBottom = () => {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight;
    autoScroll.value = true;
  }
};

const handleScroll = () => {
  if (!logContainer.value) return;
  const { scrollTop, scrollHeight, clientHeight } = logContainer.value;
  // If we scroll up, disable autoScroll
  if (scrollTop + clientHeight < scrollHeight - 50) {
    autoScroll.value = false;
  } else {
    autoScroll.value = true;
  }
};

const clearLogs = () => {
  logs.value = [];
};

watch(() => props.pod, (newPod) => {
  if (newPod.containers && newPod.containers.length > 0) {
    if (!selectedContainer.value || !newPod.containers.includes(selectedContainer.value)) {
      selectedContainer.value = newPod.containers[0];
    }
  }
  startLogStream();
}, { deep: true });

watch(selectedContainer, () => {
  startLogStream();
});

onMounted(() => {
  if (props.pod.containers && props.pod.containers.length > 0) {
    selectedContainer.value = props.pod.containers[0];
  }
  startLogStream();
});

onUnmounted(() => {
  if (abortController) {
    abortController.abort();
  }
});
</script>

<style scoped>
.log-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--panel-border);
  background: var(--panel-bg);
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-info h2 {
  font-size: 1.125rem;
  color: var(--text-primary);
  margin: 0;
}

.namespace-badge {
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.container-select {
  background: rgba(0, 0, 0, 0.3);
  color: var(--text-primary);
  border: 1px solid var(--panel-border);
  padding: 6px 12px;
  border-radius: 4px;
  outline: none;
  font-size: 0.875rem;
}

.action-btn {
  background: transparent;
  border: 1px solid var(--panel-border);
  color: var(--text-secondary);
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.action-btn.active-follow {
  color: var(--accent-color);
  border-color: rgba(56, 189, 248, 0.3);
  background: rgba(56, 189, 248, 0.1);
}

.log-stream-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  font-family: var(--font-mono);
  font-size: 0.875rem;
  line-height: 1.5;
  color: #e2e8f0;
}

.log-lines {
  display: flex;
  flex-direction: column;
}

.log-line {
  white-space: pre-wrap;
  word-break: break-all;
  padding: 2px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.02);
}

.log-line:hover {
  background: rgba(255, 255, 255, 0.03);
}

.loading-logs, .error-msg {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-secondary);
}

.error-msg {
  color: var(--danger);
}
</style>
