"""Application-level WebSocket connection manager.

This module deliberately lives outside the API package so background services can
publish events without importing API router initialization code.
"""

from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self.active_connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        connections = self.active_connections.get(user_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: dict) -> None:
        connections = self.active_connections.get(user_id)
        if not connections:
            return

        dead: Set[WebSocket] = set()
        for websocket in tuple(connections):
            try:
                await websocket.send_json(message)
            except Exception:
                dead.add(websocket)

        for websocket in dead:
            connections.discard(websocket)
        if not connections:
            self.active_connections.pop(user_id, None)

    async def broadcast(self, message: dict) -> None:
        for user_id in tuple(self.active_connections):
            await self.send_to_user(user_id, message)


manager = ConnectionManager()
