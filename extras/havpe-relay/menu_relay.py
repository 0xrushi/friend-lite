"""macOS menu bar app for the HAVPE TCP relay.

Runs the TCP-to-WebSocket relay in a background asyncio thread and shows
connection status in the macOS menu bar. No terminal needed.

Uses the same Wyoming protocol + DeviceController as main.py.
"""

import asyncio
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Optional

import rumps
import websockets
from dotenv import load_dotenv

from device_controller import DeviceController
from main import get_jwt_token

logger = logging.getLogger(__name__)

load_dotenv()

# --- Config from .env --------------------------------------------------------

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_WS_URL = os.getenv("BACKEND_WS_URL", "ws://localhost:8000")
AUTH_USERNAME = os.getenv("AUTH_USERNAME")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")
DEVICE_NAME = os.getenv("DEVICE_NAME", "havpe")
RELAY_PORT = int(os.getenv("RELAY_PORT", "8989"))


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


# --- Relay logic (Wyoming protocol, same as main.py) -------------------------

async def _forward_tcp_to_ws(
    reader: asyncio.StreamReader,
    ws,
    ws_lock: asyncio.Lock,
    state: SharedState,
) -> None:
    """Forward Wyoming messages from device TCP to backend WebSocket."""
    while True:
        line = await reader.readline()
        if not line:
            break

        line_str = line.decode().strip()
        if not line_str:
            continue

        header = json.loads(line_str)
        payload_length = header.get("payload_length", 0)

        async with ws_lock:
            await ws.send(line_str)
            if payload_length > 0:
                payload = await reader.readexactly(payload_length)
                await ws.send(payload)

        msg_type = header.get("type", "")
        if msg_type == "audio-chunk":
            with state._lock:
                state.chunks_sent += 1
        else:
            logger.info("TCP→WS: %s", msg_type)


async def _handle_backend_messages(ws, device: DeviceController) -> None:
    """Process messages from backend WebSocket, dispatch to device."""
    async for raw in ws:
        if isinstance(raw, bytes):
            continue

        try:
            msg = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue

        msg_type = msg.get("type", "")
        data = msg.get("data", {})

        if msg_type == "play-audio":
            url = data.get("url", "")
            announcement = data.get("announcement", True)
            logger.info("Backend→device: play-audio %s", url)
            await device.play_audio(url, announcement=announcement)

        elif msg_type == "led-control":
            r = float(data.get("r", 0))
            g = float(data.get("g", 0))
            b = float(data.get("b", 0))
            brightness = float(data.get("brightness", 0.3))
            duration = float(data.get("duration", 5.0))
            logger.info("Backend→device: led-control rgb=(%.1f,%.1f,%.1f) br=%.1f dur=%.1fs", r, g, b, brightness, duration)
            await device.set_led(r, g, b, brightness, duration=duration)


async def _forward_esphome_events(
    device: DeviceController,
    ws,
    ws_lock: asyncio.Lock,
) -> None:
    """Forward button/dial events from ESPHome API to backend WebSocket."""
    while True:
        event = await device.get_event()
        event_type = event.pop("type")

        wyoming_msg = json.dumps({
            "type": event_type,
            "data": event,
            "payload_length": 0,
        })
        async with ws_lock:
            await ws.send(wyoming_msg)
        logger.info("ESPHome→WS: %s %s", event_type, event)


async def handle_device(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    state: SharedState,
):
    addr = writer.get_extra_info("peername")
    device_ip = addr[0]
    addr_str = f"{addr[0]}:{addr[1]}" if addr else "unknown"
    logger.info("Device connected from %s", addr_str)
    state.update(status="connected", device_addr=addr_str, chunks_sent=0)

    token = await get_jwt_token(AUTH_USERNAME, AUTH_PASSWORD, BACKEND_URL)
    if not token:
        logger.error("Auth failed, dropping connection")
        state.update(status="listening", device_addr=None, error="Auth failed")
        writer.close()
        return

    backend_uri = f"{BACKEND_WS_URL}/ws?codec=pcm&token={token}&device_name={DEVICE_NAME}"

    device = DeviceController()

    try:
        async with websockets.connect(backend_uri) as ws:
            logger.info("Backend WS connected, starting bidirectional bridge")

            api_ok = await device.connect(device_ip)
            if api_ok:
                logger.info("ESPHome API connected — button/dial/LED/speaker enabled")
            else:
                logger.info("ESPHome API unavailable — audio-only mode")

            ws_lock = asyncio.Lock()
            tasks = [
                asyncio.create_task(_forward_tcp_to_ws(reader, ws, ws_lock, state), name="tcp→ws"),
                asyncio.create_task(_handle_backend_messages(ws, device), name="ws→device"),
            ]
            if api_ok:
                tasks.append(
                    asyncio.create_task(_forward_esphome_events(device, ws, ws_lock), name="esphome→ws")
                )

            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            for t in done:
                if t.exception():
                    logger.error("Task %s failed: %s", t.get_name(), t.exception())
                else:
                    logger.info("Task %s finished", t.get_name())

            for t in pending:
                t.cancel()

    except asyncio.IncompleteReadError:
        logger.info("Device disconnected (incomplete read)")
    except websockets.ConnectionClosed as e:
        logger.info("Backend WS closed: %s", e)
    except Exception as e:
        logger.error("Session error: %s", e)
    finally:
        await device.disconnect()
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

        token = await get_jwt_token(AUTH_USERNAME, AUTH_PASSWORD, BACKEND_URL)
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
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("aioesphomeapi").setLevel(logging.WARNING)

    state = SharedState()
    bg = AsyncioThread()
    bg.start()

    relay = RelayManager(state, bg)
    relay.start()

    app = RelayMenuApp(state, relay)
    app.run()


if __name__ == "__main__":
    main()
