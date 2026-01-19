"""
WebSocket Manager
Manages WebSocket connections for real-time progress streaming.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set

from fastapi import WebSocket

from ..models.progress import ProgressEvent

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections for real-time progress updates.

    Supports:
    - Multiple connections per job
    - Broadcasting to all connections for a job
    - Automatic cleanup on disconnect
    """

    def __init__(self):
        """Initialize the WebSocket manager."""
        # job_id -> set of active WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, job_id: str) -> None:
        """
        Accept a new WebSocket connection for a job.

        Args:
            websocket: The WebSocket connection.
            job_id: The job ID to subscribe to.
        """
        await websocket.accept()

        async with self._lock:
            if job_id not in self._connections:
                self._connections[job_id] = set()
            self._connections[job_id].add(websocket)

        logger.info(f"WebSocket connected for job {job_id}")

        # Send connected event
        event = ProgressEvent.connected(job_id)
        await self.send_personal(websocket, event)

    async def disconnect(self, websocket: WebSocket, job_id: str) -> None:
        """
        Handle WebSocket disconnection.

        Args:
            websocket: The WebSocket connection.
            job_id: The job ID that was subscribed to.
        """
        async with self._lock:
            if job_id in self._connections:
                self._connections[job_id].discard(websocket)
                if not self._connections[job_id]:
                    del self._connections[job_id]

        logger.info(f"WebSocket disconnected for job {job_id}")

    async def send_personal(self, websocket: WebSocket, event: ProgressEvent) -> bool:
        """
        Send an event to a specific WebSocket connection.

        Args:
            websocket: The WebSocket connection.
            event: The event to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            await websocket.send_json(event.model_dump(mode="json"))
            return True
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket: {e}")
            return False

    async def broadcast(self, job_id: str, event: ProgressEvent) -> int:
        """
        Broadcast an event to all connections for a job.

        Args:
            job_id: The job ID to broadcast to.
            event: The event to broadcast.

        Returns:
            Number of connections that received the event.
        """
        async with self._lock:
            connections = self._connections.get(job_id, set()).copy()

        if not connections:
            return 0

        sent = 0
        failed = []

        for websocket in connections:
            try:
                await websocket.send_json(event.model_dump(mode="json"))
                sent += 1
            except Exception as e:
                logger.warning(f"Failed to broadcast to WebSocket: {e}")
                failed.append(websocket)

        # Clean up failed connections
        if failed:
            async with self._lock:
                if job_id in self._connections:
                    for ws in failed:
                        self._connections[job_id].discard(ws)

        return sent

    def broadcast_sync(self, job_id: str, event: ProgressEvent, loop: asyncio.AbstractEventLoop) -> None:
        """
        Broadcast from a synchronous context.

        This is used when the pipeline progress callback runs in a thread pool.

        Args:
            job_id: The job ID to broadcast to.
            event: The event to broadcast.
            loop: The event loop to schedule the coroutine on.
        """
        try:
            asyncio.run_coroutine_threadsafe(
                self.broadcast(job_id, event),
                loop
            )
        except Exception as e:
            logger.error(f"Failed to schedule broadcast: {e}")

    def get_connection_count(self, job_id: str) -> int:
        """Get the number of active connections for a job."""
        return len(self._connections.get(job_id, set()))

    def get_all_job_ids(self) -> List[str]:
        """Get all job IDs with active connections."""
        return list(self._connections.keys())

    async def close_all(self, job_id: str) -> None:
        """Close all connections for a job."""
        async with self._lock:
            connections = self._connections.pop(job_id, set())

        for websocket in connections:
            try:
                await websocket.close()
            except Exception:
                pass


# Global WebSocket manager instance
ws_manager = WebSocketManager()
