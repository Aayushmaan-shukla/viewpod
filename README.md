# PodViewer

PodViewer is a lightweight, web-based application designed for monitoring Kubernetes (and k3s) pod logs in real-time. Inspired by [Dozzle](https://github.com/amir20/dozzle), it is built specifically for Kubernetes environments. 

Instead of polling for logs or storing them on disk, PodViewer directly hooks into the Kubernetes API to stream pod lifecycle events and logs seamlessly to your browser.

![PodViewer UI](frontend/public/favicon.svg)

## ✨ Features

- **Zero Storage Overhead**: Streams logs directly to your browser without writing to disk.
- **Real-Time Auto Discovery**: Uses Server-Sent Events (SSE) to automatically detect when pods start, die, or restart.
- **Auto-Reconnection**: If a pod dies and a Deployment spins up a replacement, the UI automatically connects to the new pod's logs.
- **Modern UI**: Features a beautiful glassmorphism dark-mode UI built with Vue 3.
- **Multi-Container Support**: Easily toggle between different containers running inside the same pod.
- **Fast & Lightweight**: Built with an async Python FastAPI backend (`kubernetes_asyncio`).

## 🏗 Architecture

- **Backend**: Python, FastAPI, `kubernetes_asyncio`, `sse-starlette`
- **Frontend**: Vue 3, Vite, Vanilla CSS
- **Communication**: Server-Sent Events (SSE) for pod state changes and standard HTTP chunked streaming for live logs.

## 🚀 Getting Started

### Prerequisites

- Node.js (v20.19+ or v22.12+)
- Python (3.10+)
- A working Kubernetes/k3s cluster with `~/.kube/config` properly configured.

### 1. Configure Kubernetes Access

Ensure your user has access to the cluster. If you are using **k3s**, copy the config and give it proper permissions:

```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
chmod 600 ~/.kube/config
export KUBECONFIG=~/.kube/config
```

### 2. Start the Backend (API Server)

The backend handles the connection to the Kubernetes API and proxies the streams.

```bash
cd backend
pip install -r requirements.txt

# Start the server (listening on all interfaces)
uvicorn main:app --host 0.0.0.0 --reload
```

The backend will start running at `http://<SERVER_IP>:8000`.

### 3. Start the Frontend (UI)

The frontend is a Vue application that dynamically connects to your backend based on the URL it is loaded from.

```bash
cd frontend

# Ensure you are on a compatible Node version
nvm use 20

# Install dependencies
npm install

# Start the Vite dev server (exposed to network)
npm run dev -- --host
```

The frontend will start running at `http://<SERVER_IP>:5173`. Open this URL in your browser to view your pods!

## ⚙️ How It Works

1. **API Discovery**: The backend uses the official `kubernetes_asyncio` library to parse your local `~/.kube/config` or an in-cluster Service Account.
2. **Watchers**: It establishes a `Watch()` stream against the Kubernetes CoreV1 API to monitor pod events (`ADDED`, `MODIFIED`, `DELETED`).
3. **SSE Broadcast**: These events are piped to the Vue frontend via `EventSource`.
4. **Log Stream**: When you click a pod, the backend calls `read_namespaced_pod_log(follow=True)` and yields a `StreamingResponse` directly to the browser's `fetch` reader.

## 📄 License

MIT License
