from __future__ import annotations

from .types import Receive, Scope, Send


class WebSocketDisconnect(Exception):
    def __init__(self, code: int = 1000) -> None:
        self.code = code


class WebSocket:
    """Thin state machine over the `websocket.*` ASGI events."""

    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["type"] == "websocket"
        self.scope = scope
        self._receive = receive
        self._send = send
        self.path_params: dict[str, object] = dict(scope.get("path_params", {}))

    async def accept(self, subprotocol: str | None = None) -> None:
        msg = await self._receive()
        assert msg["type"] == "websocket.connect", msg["type"]
        await self._send({"type": "websocket.accept", "subprotocol": subprotocol})

    async def receive_text(self) -> str:
        msg = await self._receive()
        if msg["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(msg.get("code", 1000))
        return str(msg.get("text", ""))

    async def send_text(self, data: str) -> None:
        await self._send({"type": "websocket.send", "text": data})

    async def close(self, code: int = 1000) -> None:
        await self._send({"type": "websocket.close", "code": code})
