"""macOS menu bar app for the HAVPE TCP relay.

Runs the TCP-to-WebSocket relay in a background asyncio thread and shows
connection status in the macOS menu bar. No terminal needed.
"""

import asyncio
import logging
import os
import struct
import threading
from dataclasses import dataclass, field
from typing import Optional

import httpx
import rumps
import websockets
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

# --- Config from .env --------------------------------------------------------

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_WS_URL = os.getenv("BACKEND_WS_URL", "ws://localhost:8000")
AUTH_USERNAME = os.getenv("AUTH_USERNAME")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")
DEVICE_NAME = os.getenv("DEVICE_NAME", "havpe")
RELAY_PORT = int(os.getenv("RELAY_PORT", "8989"))

MSG_AUDIO = 0x01
MSG_BUTTON = 0x02
BUTTON_NAMES = {1: "SINGLE_PRESS", 2: "DOUBLE_PRESS", 3: "LONG_PRESS"}


# --- Shared state ------------------------------------------------------------

@dataclass
class SharedState:
    """Thread-safe state shared between rumps UI and the asyncio relay thread."""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    status: str = "idle"  # idle | listening | connected | error
    error: Optional[str] = None
    device_addr: Optional[str] = None
    chunks_sent: int = 0

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "status": self.status,
                "error": self.error,
                "device_addr": self.device_addr,
                "chunks_sent": self.chunks_sent,
            }

    def update(self, **kwargs) -> None:
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)


# --- Asyncio background thread -----------------------------------------------

class AsyncioThread:
    """Runs an asyncio event loop in a daemon thread."""

    def __init__(self) -> None:
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        while self.loop is None or not self.loop.is_running():
            threading.Event().wait(0.01)

    def _run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_coro(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)


# --- Relay logic (inlined from main.py) --------------------------------------

async def get_jwt_token() -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{BACKEND_URL}/auth/jwt/login",
                data={"username": AUTH_USERNAME, "password": AUTH_PASSWORD},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            if token:
                logger.info("Auth OK")
                return token
        logger.error("Auth failed: %d", resp.status_code)
    except Exception as e:
        logger.error("Auth error: %s", e)
    return None


async def handle_device(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    state: SharedState,
):
    addr = writer.get_extra_info("peername")
    addr_str = f"{addr[0]}:{addr[1]}" if addr else "unknown"
    logger.info("Device connected from %s", addr_str)
    state.update(status="connected", device_addr=addr_str, chunks_sent=0)

    token = await get_jwt_token()
    if not token:
        logger.error("Auth failed, dropping connection")
        state.update(status="listening", device_addr=None, error="Auth failed")
        writer.close()
        return

    backend_uri = f"{BACKEND_WS_URL}/ws?codec=pcm&token={token}&device_name={DEVICE_NAME}"
    try:
        async with websockets.connect(backend_uri) as ws:
            logger.info("Backend WS connected, proxying")
            await ws.send(
                '{"type":"audio-start","data":{"rate":16000,"width":2,"channels":1,"mode":"streaming"},"payload_length":0}'
            )

            # Drain incoming WS messages (interim transcripts, etc.) so the
            # buffer doesn't fill up and kill the connection.
            async def _drain_ws():
                try:
                    async for msg in ws:
                        logger.debug("Backend→relay (discarded): %s", str(msg)[:80])
                except websockets.ConnectionClosed:
                    pass

            drain_task = asyncio.create_task(_drain_ws())

            try:
                while True:
                    hdr = await reader.readexactly(3)
                    msg_type = hdr[0]
                    payload_len = struct.unpack("!H", hdr[1:3])[0]
                    payload = await reader.readexactly(payload_len) if payload_len else b""

                    if msg_type == MSG_AUDIO:
                        header = f'{{"type":"audio-chunk","data":{{"rate":16000,"width":2,"channels":1}},"payload_length":{payload_len}}}'
                        await ws.send(header)
                        await ws.send(payload)
                        with state._lock:
                            state.chunks_sent += 1
                    elif msg_type == MSG_BUTTON:
                        code = payload[0] if payload else 0
                        name = BUTTON_NAMES.get(code, f"UNKNOWN_{code}")
                        logger.info("Button: %s", name)
                        await ws.send(
                            f'{{"type":"button-event","data":{{"state":"{name}"}},"payload_length":0}}'
                        )
                    else:
                        logger.warning("Unknown msg type: 0x%02x", msg_type)
            finally:
                drain_task.cancel()

    except asyncio.IncompleteReadError:
        logger.info("Device disconnected")
    except websockets.ConnectionClosed as e:
        logger.info("Backend WS closed: %s", e)
    except Exception as e:
        logger.error("Session error: %s", e)
    finally:
        writer.close()
        state.update(status="listening", device_addr=None)
        logger.info("Session ended")


# --- Relay manager ------------------------------------------------------------

class RelayManager:
    """Manages the TCP relay server lifecycle in the background asyncio thread."""

    def __init__(self, state: SharedState, bg: AsyncioThread) -> None:
        self.state = state
        self.bg = bg
        self._server: Optional[asyncio.AbstractServer] = None

    def start(self) -> None:
        self.bg.run_coro(self._start_server())

    def stop(self) -> None:
        self.bg.run_coro(self._stop_server())

    async def _start_server(self) -> None:
        if self._server is not None:
            return

        if not AUTH_USERNAME or not AUTH_PASSWORD:
            self.state.update(status="error", error="AUTH_USERNAME/AUTH_PASSWORD not set in .env")
            return

        token = await get_jwt_token()
        if not token:
            self.state.update(status="error", error="Backend auth failed")
            return

        def client_handler(r, w):
            asyncio.ensure_future(handle_device(r, w, self.state))

        self._server = await asyncio.start_server(client_handler, "0.0.0.0", RELAY_PORT)
        self.state.update(status="listening", error=None)
        logger.info("Relay listening on :%d", RELAY_PORT)

    async def _stop_server(self) -> None:
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()
        self._server = None
        self.state.update(status="idle", device_addr=None, chunks_sent=0)
        logger.info("Relay stopped")


# --- rumps menu bar app -------------------------------------------------------

class RelayMenuApp(rumps.App):
    """macOS menu bar app for the HAVPE relay."""

    def __init__(self, state: SharedState, relay: RelayManager) -> None:
        super().__init__("Chronicle Relay", title="\u2299\u02b0\u1d43")
        self.state = state
        self.relay = relay

        self.status_item = rumps.MenuItem("Status: Starting...", callback=None)
        self.toggle_item = rumps.MenuItem("Stop Relay", callback=self.on_toggle)

        self.menu = [
            self.status_item,
            None,
            self.toggle_item,
            None,
        ]

    @rumps.timer(2)
    def refresh_ui(self, _sender) -> None:
        snap = self.state.snapshot()
        status = snap["status"]

        if status == "connected":
            self.title = "\u25cf\u02b0\u1d43"  # filled circle + ha
            addr = snap["device_addr"] or "?"
            chunks = f"{snap['chunks_sent']:,}"
            self.status_item.title = f"Status: Connected ({addr}) \u2014 {chunks} chunks"
            self.toggle_item.title = "Stop Relay"
        elif status == "listening":
            self.title = "\u2299\u02b0\u1d43"  # circled dot + ha
            self.status_item.title = f"Status: Listening on :{RELAY_PORT}"
            self.toggle_item.title = "Stop Relay"
        elif status == "error":
            self.title = "\u2298\u02b0\u1d43"  # circled division slash + ha
            self.status_item.title = f"Status: Error \u2014 {snap['error'] or 'unknown'}"
            self.toggle_item.title = "Start Relay"
        else:
            self.title = "\u2298\u02b0\u1d43"  # stopped + ha
            self.status_item.title = "Status: Stopped"
            self.toggle_item.title = "Start Relay"

    def on_toggle(self, _sender) -> None:
        snap = self.state.snapshot()
        if snap["status"] in ("listening", "connected"):
            logger.info("User stopping relay")
            self.relay.stop()
        else:
            logger.info("User starting relay")
            self.relay.start()


# --- Entry point --------------------------------------------------------------

def main() -> None:
    from AppKit import NSApplication
    NSApplication.sharedApplication().setActivationPolicy_(1)

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )

    state = SharedState()
    bg = AsyncioThread()
    bg.start()

    relay = RelayManager(state, bg)
    relay.start()

    app = RelayMenuApp(state, relay)
    app.run()


if __name__ == "__main__":
    main()
