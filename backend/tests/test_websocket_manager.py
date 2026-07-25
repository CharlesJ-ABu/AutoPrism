import asyncio

from app.core.websocket import ConnectionManager


class FakeSocket:
    def __init__(self):
        self.accepted = False
        self.messages = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, message):
        self.messages.append(message)


def test_connection_manager_broadcast_and_disconnect() -> None:
    manager = ConnectionManager()
    socket = FakeSocket()
    asyncio.run(manager.connect(socket, "local"))
    asyncio.run(manager.broadcast({"type": "test"}))
    assert socket.accepted
    assert socket.messages == [{"type": "test"}]
    manager.disconnect(socket, "local")
    assert manager.active_connections == {}
