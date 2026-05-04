"""WebSocket endpoint for real-time notification delivery."""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_token

logger = logging.getLogger("mica.websocket")

router = APIRouter()

# user_id -> list of active WebSocket connections
active_connections: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket, token: str = ""):
    """WebSocket endpoint for real-time notification push.

    Authenticates via JWT token query parameter.
    Keeps connection alive and pushes notification events to the user.
    """
    if not token:
        await websocket.close(code=4001, reason="missing_token")
        return

    try:
        payload = decode_token(token)
        user_id = payload.get("sub", "")
    except Exception:
        await websocket.close(code=4001, reason="invalid_token")
        return

    if not user_id:
        await websocket.close(code=4001, reason="invalid_token")
        return

    await websocket.accept()

    if user_id not in active_connections:
        active_connections[user_id] = []
    active_connections[user_id].append(websocket)

    logger.info("ws: user=%s connected (total=%d)", user_id, len(active_connections[user_id]))

    try:
        while True:
            # Keep connection alive; client may send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.debug("ws: user=%s connection error", user_id, exc_info=True)
    finally:
        if user_id in active_connections:
            try:
                active_connections[user_id].remove(websocket)
                if not active_connections[user_id]:
                    del active_connections[user_id]
            except (ValueError, KeyError):
                pass
        logger.info("ws: user=%s disconnected", user_id)


async def notify_user(user_id: str, data: dict) -> None:
    """Push a JSON message to all WebSocket connections for the given user.

    Args:
        user_id: The user's UUID as a string.
        data: JSON-serializable dict to send.
    """
    if user_id not in active_connections:
        return

    dead: list[WebSocket] = []
    for ws in active_connections[user_id]:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)

    for ws in dead:
        try:
            active_connections[user_id].remove(ws)
        except ValueError:
            pass

    if user_id in active_connections and not active_connections[user_id]:
        del active_connections[user_id]
