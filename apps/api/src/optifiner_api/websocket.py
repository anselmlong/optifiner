"""WebSocket manager for real-time updates."""

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        # workflow_id -> list of WebSocket connections
        self.workflow_connections: dict[str, list[WebSocket]] = {}
        # Global log connections (for dashboard)
        self.global_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect_workflow(self, websocket: WebSocket, workflow_id: str) -> None:
        """Connect a WebSocket to a specific workflow."""
        await websocket.accept()
        async with self._lock:
            if workflow_id not in self.workflow_connections:
                self.workflow_connections[workflow_id] = []
            self.workflow_connections[workflow_id].append(websocket)
        logger.info(f"WebSocket connected to workflow {workflow_id}")

    async def connect_global(self, websocket: WebSocket) -> None:
        """Connect a WebSocket to global updates."""
        await websocket.accept()
        async with self._lock:
            self.global_connections.append(websocket)
        logger.info("WebSocket connected to global updates")

    async def disconnect_workflow(self, websocket: WebSocket, workflow_id: str) -> None:
        """Disconnect a WebSocket from a workflow."""
        async with self._lock:
            if workflow_id in self.workflow_connections:
                if websocket in self.workflow_connections[workflow_id]:
                    self.workflow_connections[workflow_id].remove(websocket)
                if not self.workflow_connections[workflow_id]:
                    del self.workflow_connections[workflow_id]
        logger.info(f"WebSocket disconnected from workflow {workflow_id}")

    async def disconnect_global(self, websocket: WebSocket) -> None:
        """Disconnect a WebSocket from global updates."""
        async with self._lock:
            if websocket in self.global_connections:
                self.global_connections.remove(websocket)
        logger.info("WebSocket disconnected from global updates")

    async def broadcast_to_workflow(self, workflow_id: str, message: dict[str, Any]) -> None:
        """Broadcast a message to all connections for a workflow."""
        workflow_id_str = str(workflow_id) if isinstance(workflow_id, UUID) else workflow_id
        async with self._lock:
            connections = self.workflow_connections.get(workflow_id_str, [])
            if not connections:
                return
            
            dead_connections = []
            for websocket in connections:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to websocket: {e}")
                    dead_connections.append(websocket)
            
            # Clean up dead connections
            for ws in dead_connections:
                if ws in self.workflow_connections.get(workflow_id_str, []):
                    self.workflow_connections[workflow_id_str].remove(ws)

    async def broadcast_global(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all global connections."""
        async with self._lock:
            dead_connections = []
            for websocket in self.global_connections:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to websocket: {e}")
                    dead_connections.append(websocket)
            
            # Clean up dead connections
            for ws in dead_connections:
                if ws in self.global_connections:
                    self.global_connections.remove(ws)

    async def send_workflow_update(
        self,
        workflow_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Send a workflow update event."""
        message = {
            "type": event_type,
            "workflow_id": workflow_id,
            "data": data,
        }
        await self.broadcast_to_workflow(workflow_id, message)
        # Also send to global for dashboard
        await self.broadcast_global(message)

    async def send_agent_update(
        self,
        workflow_id: str,
        agent_data: dict[str, Any],
    ) -> None:
        """Send an agent update event."""
        await self.send_workflow_update(
            workflow_id,
            "agent_update",
            agent_data,
        )

    async def send_log(
        self,
        workflow_id: str,
        level: str,
        message: str,
        agent_name: str | None = None,
        details: str | None = None,
    ) -> None:
        """Send a log entry."""
        from datetime import datetime
        
        log_data = {
            "level": level,
            "message": message,
            "agent_name": agent_name,
            "details": details,
            "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        }
        await self.send_workflow_update(workflow_id, "log", log_data)

    async def send_step_update(
        self,
        workflow_id: str,
        step_data: dict[str, Any],
    ) -> None:
        """Send a step/improvement update."""
        await self.send_workflow_update(workflow_id, "step", step_data)

    async def send_status_update(
        self,
        workflow_id: str,
        status: str,
        extra_data: dict[str, Any] | None = None,
    ) -> None:
        """Send a status update."""
        data = {"status": status}
        if extra_data:
            data.update(extra_data)
        await self.send_workflow_update(workflow_id, "status", data)


# Global connection manager instance
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager."""
    return manager
