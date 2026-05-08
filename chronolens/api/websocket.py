"""WebSocket endpoint stub: /ws/live — real-time activity push."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

_connections: list[WebSocket] = []


@router.websocket("/ws/live")
async def live_feed(websocket: WebSocket) -> None:
    """Accept a WebSocket connection and push live activity events.

    Sends a heartbeat ping every 30 seconds when idle.
    Phase 1 will replace the heartbeat with real capture events.
    """
    await websocket.accept()
    _connections.append(websocket)
    logger.info("WebSocket client connected (total=%d)", len(_connections))
    try:
        await websocket.send_text(json.dumps({"type": "connected", "version": "0.1.0"}))
        while True:
            try:
                # Wait for client messages (e.g. ping) with a timeout.
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                msg: dict[str, Any] = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except TimeoutError:
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
    except WebSocketDisconnect:
        pass
    finally:
        _connections.remove(websocket)
        logger.info("WebSocket client disconnected (total=%d)", len(_connections))


async def broadcast(event: dict[str, Any]) -> None:
    """Broadcast an event to all connected WebSocket clients.

    Args:
        event: JSON-serialisable event dict.
    """
    payload = json.dumps(event)
    dead: list[WebSocket] = []
    for ws in list(_connections):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _connections:
            _connections.remove(ws)
