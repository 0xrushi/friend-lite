#!/usr/bin/env python3
"""
HAVPE Relay - Bidirectional TCP/ESPHome→WebSocket bridge for Chronicle.

Two connections to the device:
  TCP (:8989)         — audio streaming (device → relay → backend)
  ESPHome API (:6053) — button/dial events (device → backend),
                        LED control + audio playback (backend → device)

All events are forwarded to/from the backend WebSocket using Wyoming protocol.
"""

import argparse
import asyncio
import json
import logging
import os
import time
import wave

import httpx
import websockets

from device_controller import DeviceController

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_WS_URL = os.getenv("BACKEND_WS_URL", "ws://localhost:8000")
AUTH_USERNAME = os.getenv("AUTH_USERNAME")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")
DEVICE_NAME = os.getenv("DEVICE_NAME", "havpe")


async def get_jwt_token(username: str, password: str, backend_url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{backend_url}/auth/jwt/login",
                data={"username": username, "password": password},
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


async def _forward_tcp_to_ws(
    reader: asyncio.StreamReader,
    ws,
    ws_lock: asyncio.Lock,
    dump_dir: str | None = None,
) -> None:
    """Forward Wyoming messages from device TCP to backend WebSocket."""
    wav_file: wave.Wave_write | None = None
    chunk_count = 0
    total_bytes = 0
    t_start: float | None = None
    declared_rate = 16000
    declared_width = 2
    declared_channels = 1

    def _open_wav(rate: int, width: int, channels: int) -> wave.Wave_write | None:
        if not dump_dir:
            return None
        os.makedirs(dump_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(dump_dir, f"havpe_debug_{ts}.wav")
        wf = wave.open(path, "wb")
        wf.setnchannels(channels)
        wf.setsampwidth(width)
        wf.setframerate(rate)
        logger.info("Debug audio dump: %s (rate=%d width=%d ch=%d)", path, rate, width, channels)
        return wf

    try:
        while True:
            line = await reader.readline()
            if not line:
                break  # Device disconnected

            line_str = line.decode().strip()
            if not line_str:
                continue

            header = json.loads(line_str)
            payload_length = header.get("payload_length", 0)

            # Lock ensures text+binary pair is sent atomically (no interleaving
            # with button/dial events from the ESPHome task)
            async with ws_lock:
                await ws.send(line_str)
                if payload_length > 0:
                    payload = await reader.readexactly(payload_length)
                    await ws.send(payload)

            msg_type = header.get("type", "")

            if msg_type == "audio-start" and dump_dir:
                d = header.get("data", {})
                declared_rate = d.get("rate", 16000)
                declared_width = d.get("width", 2)
                declared_channels = d.get("channels", 1)
                wav_file = _open_wav(declared_rate, declared_width, declared_channels)
                chunk_count = 0
                total_bytes = 0
                t_start = time.monotonic()

            elif msg_type == "audio-chunk":
                if wav_file and payload_length > 0:
                    wav_file.writeframes(payload)
                chunk_count += 1
                total_bytes += payload_length
                if t_start is None:
                    t_start = time.monotonic()
                # Log stats every 100 chunks
                if dump_dir and chunk_count % 100 == 0:
                    elapsed = time.monotonic() - t_start
                    byte_rate = total_bytes / elapsed if elapsed > 0 else 0
                    expected_rate = declared_rate * declared_width * declared_channels
                    ratio = byte_rate / expected_rate if expected_rate > 0 else 0
                    logger.info(
                        "Audio stats: %d chunks, %d bytes, %.1fs elapsed, "
                        "%.0f B/s actual vs %d B/s declared (ratio=%.2fx)",
                        chunk_count, total_bytes, elapsed, byte_rate, expected_rate, ratio,
                    )

            elif msg_type == "audio-stop" and dump_dir:
                if t_start:
                    elapsed = time.monotonic() - t_start
                    byte_rate = total_bytes / elapsed if elapsed > 0 else 0
                    expected_rate = declared_rate * declared_width * declared_channels
                    ratio = byte_rate / expected_rate if expected_rate > 0 else 0
                    declared_duration = total_bytes / expected_rate if expected_rate > 0 else 0
                    logger.info(
                        "Session end: %d chunks, %d bytes in %.1fs wall-clock | "
                        "%.0f B/s actual vs %d B/s expected (ratio=%.2fx) | "
                        "declared duration=%.1fs",
                        chunk_count, total_bytes, elapsed, byte_rate, expected_rate,
                        ratio, declared_duration,
                    )

            if msg_type != "audio-chunk":
                logger.info("TCP→WS: %s", msg_type)
    finally:
        if wav_file:
            wav_file.close()
            logger.info("Debug WAV closed (%d bytes written)", total_bytes)


async def _handle_backend_messages(ws, device: DeviceController) -> None:
    """Process messages from backend WebSocket, dispatch to device."""
    async for raw in ws:
        if isinstance(raw, bytes):
            logger.debug("Backend binary message (%d bytes), discarded", len(raw))
            continue

        try:
            msg = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.debug("Backend non-JSON message, discarded: %s", str(raw)[:80])
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

        else:
            logger.debug("Backend→relay (ignored): %s", msg_type or str(raw)[:80])


async def _forward_esphome_events(device: DeviceController, ws, ws_lock: asyncio.Lock) -> None:
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
    dump_dir: str | None = None,
):
    addr = writer.get_extra_info("peername")
    device_ip = addr[0]
    logger.info("Device connected from %s", addr)

    token = await get_jwt_token(AUTH_USERNAME, AUTH_PASSWORD, BACKEND_URL)
    if not token:
        logger.error("Auth failed, dropping connection")
        writer.close()
        return

    backend_uri = (
        f"{BACKEND_WS_URL}/ws?codec=pcm&token={token}&device_name={DEVICE_NAME}"
    )

    device = DeviceController()

    try:
        async with websockets.connect(backend_uri) as ws:
            logger.info("Backend WS connected, starting bidirectional bridge")

            # ESPHome API connection (best-effort)
            api_ok = await device.connect(device_ip)
            if api_ok:
                logger.info("ESPHome API connected — button/dial/LED/speaker enabled")
            else:
                logger.info("ESPHome API unavailable — audio-only mode")

            ws_lock = asyncio.Lock()
            tasks = [
                asyncio.create_task(
                    _forward_tcp_to_ws(reader, ws, ws_lock, dump_dir=dump_dir),
                    name="tcp→ws",
                ),
                asyncio.create_task(_handle_backend_messages(ws, device), name="ws→device"),
            ]
            if api_ok:
                tasks.append(
                    asyncio.create_task(_forward_esphome_events(device, ws, ws_lock), name="esphome→ws")
                )

            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            # Log which task finished first
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
        logger.info("Session ended")


async def main():
    global BACKEND_URL, BACKEND_WS_URL, AUTH_USERNAME, AUTH_PASSWORD, DEVICE_NAME

    parser = argparse.ArgumentParser(
        description="HAVPE Relay - Bidirectional Wyoming bridge"
    )
    parser.add_argument("--port", type=int, default=8989)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--backend-url", type=str, default=BACKEND_URL)
    parser.add_argument("--backend-ws-url", type=str, default=BACKEND_WS_URL)
    parser.add_argument("--username", type=str, default=AUTH_USERNAME)
    parser.add_argument("--password", type=str, default=AUTH_PASSWORD)
    parser.add_argument("--device-name", type=str, default=DEVICE_NAME)
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument(
        "--dump-audio",
        metavar="DIR",
        default=None,
        help="Dump raw device audio to WAV files in DIR (for debugging sample-rate mismatches)",
    )
    args = parser.parse_args()

    BACKEND_URL = args.backend_url
    BACKEND_WS_URL = args.backend_ws_url
    AUTH_USERNAME = args.username
    AUTH_PASSWORD = args.password
    DEVICE_NAME = args.device_name

    level = logging.WARNING - (10 * min(args.verbose, 2))
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=level)

    # Silence noisy third-party loggers
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("aioesphomeapi").setLevel(logging.WARNING)

    if not AUTH_USERNAME or not AUTH_PASSWORD:
        logger.error(
            "Set AUTH_USERNAME and AUTH_PASSWORD (env or --username/--password)"
        )
        return

    token = await get_jwt_token(AUTH_USERNAME, AUTH_PASSWORD, BACKEND_URL)
    if not token:
        logger.error("Startup auth check failed")
        return

    dump_dir = args.dump_audio
    if dump_dir:
        logger.info("Audio dump enabled → %s", dump_dir)

    server = await asyncio.start_server(
        lambda r, w: handle_device(r, w, dump_dir=dump_dir),
        args.host,
        args.port,
    )
    logger.info("Relay listening on %s:%d (TCP)", args.host, args.port)
    logger.info("Backend: %s", BACKEND_URL)

    async with server:
        await server.serve_forever()


def cli():
    """Entry point with subcommands for service management."""
    import sys

    parser = argparse.ArgumentParser(description="HAVPE Relay")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("menu", help="Launch menu bar app (default)")
    sub.add_parser("relay", help="Run CLI relay (no menu bar)")
    sub.add_parser("install", help="Install as macOS login service")
    sub.add_parser("uninstall", help="Remove macOS login service")
    sub.add_parser("kickstart", help="Relaunch the menu bar app")
    sub.add_parser("status", help="Show service status")
    sub.add_parser("logs", help="Tail service logs")

    args = parser.parse_args()
    command = args.command or "menu"

    if command == "menu":
        from menu_relay import main as menu_main
        menu_main()
    elif command == "relay":
        # Run CLI relay with remaining args
        sys.argv = [sys.argv[0]] + sys.argv[2:]  # strip subcommand
        asyncio.run(main())
    elif command == "install":
        from service import install
        install()
    elif command == "uninstall":
        from service import uninstall
        uninstall()
    elif command == "kickstart":
        from service import kickstart
        kickstart()
    elif command == "status":
        from service import status
        status()
    elif command == "logs":
        from service import logs
        logs()


if __name__ == "__main__":
    # If called with no args or a subcommand, use cli()
    # If called with flags like --port, --backend-url, fall through to relay
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in ("menu", "relay", "install", "uninstall", "kickstart", "status", "logs"):
        cli()
    else:
        asyncio.run(main())
