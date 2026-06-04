import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient
from kubernetes_asyncio.watch import Watch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("podviewer")

app = FastAPI(title="PodViewer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global clients
core_v1_api = None

@app.on_event("startup")
async def startup_event():
    global core_v1_api
    try:
        # Try loading in-cluster config first (if running inside k8s)
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config.")
    except config.ConfigException:
        # Fallback to local kubeconfig
        await config.load_kube_config()
        logger.info("Loaded local kubeconfig.")
    
    core_v1_api = client.CoreV1Api()

@app.on_event("shutdown")
async def shutdown_event():
    if core_v1_api:
        await core_v1_api.api_client.close()

def format_pod(pod):
    return {
        "name": pod.metadata.name,
        "namespace": pod.metadata.namespace,
        "status": pod.status.phase,
        "labels": pod.metadata.labels or {},
        "created_at": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
        "containers": [c.name for c in pod.spec.containers] if pod.spec.containers else []
    }

@app.get("/api/pods")
async def list_pods(namespace: str = ""):
    """List all pods (or in a specific namespace)."""
    if namespace:
        pods = await core_v1_api.list_namespaced_pod(namespace)
    else:
        pods = await core_v1_api.list_pod_for_all_namespaces()
    
    return [format_pod(pod) for pod in pods.items]

@app.get("/api/events")
async def stream_events():
    """Stream pod lifecycle events via SSE."""
    async def event_generator() -> AsyncGenerator[dict, None]:
        w = Watch()
        try:
            # We watch all namespaces. If you want to restrict, use list_namespaced_pod.
            async for event in w.stream(core_v1_api.list_pod_for_all_namespaces):
                event_type = event['type']
                pod = event['object']
                yield {
                    "event": event_type,  # ADDED, MODIFIED, DELETED
                    "data": json.dumps(format_pod(pod))
                }
        except asyncio.CancelledError:
            w.stop()
            logger.info("Event stream cancelled by client.")

    return EventSourceResponse(event_generator())

@app.get("/api/logs/{namespace}/{pod_name}")
async def stream_logs(namespace: str, pod_name: str, container: str = None):
    """Stream logs for a specific pod."""
    
    async def log_generator():
        try:
            kwargs = {
                "name": pod_name,
                "namespace": namespace,
                "follow": True,
                "timestamps": True,
                "_preload_content": False
            }
            if container:
                kwargs["container"] = container

            # Note: _preload_content=False returns a urllib3 response or an aiohttp ClientResponse
            # Since kubernetes_asyncio uses aiohttp under the hood:
            resp = await core_v1_api.read_namespaced_pod_log(**kwargs)
            
            # Read lines asynchronously
            async for line in resp.content:
                if line:
                    yield line.decode('utf-8')
        except Exception as e:
            logger.error(f"Error streaming logs for {pod_name}: {e}")
            yield f"Error streaming logs: {e}\n"

    return StreamingResponse(log_generator(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
