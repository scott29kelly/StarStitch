"""
WebSocket Handler
Real-time progress updates for render jobs.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect

from .job_queue import job_queue
from .models import JobState, WebSocketMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for render progress updates.
    
    Tracks active connections per job_id and handles message broadcasting.
    """

    def __init__(self):
        # job_id -> set of websocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> job_id for reverse lookup
        self._websocket_jobs: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, job_id: str) -> bool:
        """
        Accept a WebSocket connection for a job.
        
        Args:
            websocket: The WebSocket connection.
            job_id: The job to subscribe to.
            
        Returns:
            True if connection was accepted.
        """
        # Verify job exists
        job = job_queue.get_job(job_id)
        if not job:
            await websocket.close(code=4004, reason=f"Job '{job_id}' not found")
            return False
        
        await websocket.accept()
        
        # Track connection
        if job_id not in self._connections:
            self._connections[job_id] = set()
        self._connections[job_id].add(websocket)
        self._websocket_jobs[websocket] = job_id
        
        # Register callback for this connection
        async def progress_callback(event_type: str, data: dict):
            await self._send_to_websocket(websocket, job_id, event_type, data)
        
        job_queue.register_progress_callback(job_id, progress_callback)
        
        logger.info(f"WebSocket connected for job {job_id}")
        
        # Send current state
        await self._send_current_state(websocket, job)
        
        return True

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        job_id = self._websocket_jobs.pop(websocket, None)
        
        if job_id and job_id in self._connections:
            self._connections[job_id].discard(websocket)
            if not self._connections[job_id]:
                del self._connections[job_id]
        
        logger.info(f"WebSocket disconnected for job {job_id}")

    async def _send_to_websocket(
        self,
        websocket: WebSocket,
        job_id: str,
        event_type: str,
        data: dict,
    ):
        """Send a message to a specific WebSocket."""
        try:
            message = WebSocketMessage(
                type=event_type,
                job_id=job_id,
                data=data,
                timestamp=datetime.now(),
            )
            await websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")

    async def _send_current_state(self, websocket: WebSocket, job):
        """Send the current state of a job to a new connection."""
        event_type = "state"
        
        data = {
            "state": job.state.value,
            "created_at": job.created_at.isoformat(),
        }
        
        if job.progress:
            data["progress"] = job.progress.model_dump()
        
        if job.state == JobState.COMPLETE:
            event_type = "complete"
            data["output_path"] = job.output_path
            data["variant_paths"] = job.variant_paths
        elif job.state == JobState.FAILED:
            event_type = "error"
            data["message"] = job.error_message
        elif job.state == JobState.CANCELLED:
            event_type = "cancelled"
        
        await self._send_to_websocket(websocket, job.job_id, event_type, data)

    async def broadcast(self, job_id: str, event_type: str, data: dict):
        """Broadcast a message to all connections for a job."""
        connections = self._connections.get(job_id, set())
        
        if not connections:
            return
        
        message = WebSocketMessage(
            type=event_type,
            job_id=job_id,
            data=data,
            timestamp=datetime.now(),
        )
        message_text = message.model_dump_json()
        
        # Send to all connections
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_text(message_text)
            except Exception:
                disconnected.append(websocket)
        
        # Clean up disconnected
        for ws in disconnected:
            await self.disconnect(ws)

    def get_connection_count(self, job_id: str) -> int:
        """Get the number of connections for a job."""
        return len(self._connections.get(job_id, set()))


# Global connection manager
connection_manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint handler.
    
    Maintains a connection for real-time render progress updates.
    
    Messages sent:
    - state: Initial state when connecting
    - progress: Step-by-step progress updates
    - complete: Render finished successfully
    - error: Render failed with error
    - cancelled: Render was cancelled
    
    Messages received:
    - ping: Heartbeat (responds with pong)
    - cancel: Request job cancellation
    """
    connected = await connection_manager.connect(websocket, job_id)
    
    if not connected:
        return
    
    try:
        while True:
            # Wait for client messages
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # Heartbeat timeout
                )
                
                # Parse message
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "")
                    
                    if msg_type == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "job_id": job_id,
                            "timestamp": datetime.now().isoformat(),
                        }))
                    elif msg_type == "cancel":
                        job_queue.cancel_job(job_id)
                        await websocket.send_text(json.dumps({
                            "type": "cancel_requested",
                            "job_id": job_id,
                            "timestamp": datetime.now().isoformat(),
                        }))
                    else:
                        logger.debug(f"Unknown WebSocket message type: {msg_type}")
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in WebSocket message: {message}")
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat",
                        "job_id": job_id,
                        "timestamp": datetime.now().isoformat(),
                    }))
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        pass
    finally:
        await connection_manager.disconnect(websocket)
