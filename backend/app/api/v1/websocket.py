# Tech Nebula - WebSocket Route
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.v1.ws import manager
from app.core.security import decode_access_token

router = APIRouter()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time feed updates."""
    # Optionally verify token from query param
    token = websocket.query_params.get("token")
    if token:
        payload = decode_access_token(token)
        if not payload or payload.get("sub") != user_id:
            await websocket.close(code=4001)
            return

    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await websocket.receive_text()
            # Echo back or handle commands
            await websocket.send_json({"type": "pong", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
