#!/usr/bin/env python3
"""
HAVPE Relay - TCP→WebSocket bridge for Chronicle.

ESP32 sends framed TCP: [type:1][length:2][payload]
  type 0x01 = audio PCM, type 0x02 = button code

This relay wraps it in Wyoming protocol and forwards to the backend.
"""

import argparse
import asyncio
import logging
import os
import struct

import httpx
import websockets

logger = logging.getLogger(__name__)

# Message types (match chronicle.h)
MSG_AUDIO = 0x01
MSG_BUTTON = 0x02

BUTTON_NAMES = {1: "SINGLE_PRESS", 2: "DOUBLE_PRESS", 3: "LONG_PRESS"}

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_WS_URL = os.getenv("BACKEND_WS_URL", "ws://localhost:8000")
AUTH_USERNAME = os.getenv("AUTH_USERNAME")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")
DEVICE_NAME = os.getenv("DEVICE_NAME", "havpe")
SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))
SAMPLE_WIDTH = int(os.getenv("SAMPLE_WIDTH", "2"))
CHANNELS = int(os.getenv("CHANNELS", "1"))


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


async def read_exact(reader: asyncio.StreamReader, n: int) -> bytes:
    """Read exactly n bytes or raise."""
    data = await reader.readexactly(n)
    return data


async def handle_device(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    logger.info("Device connected from %s", addr)

    token = await get_jwt_token(AUTH_USERNAME, AUTH_PASSWORD, BACKEND_URL)
    if not token:
        logger.error("Auth failed, dropping connection")
        writer.close()
        return

    backend_uri = (
        f"{BACKEND_WS_URL}/ws?codec=pcm&token={token}&device_name={DEVICE_NAME}"
    )

    try:
        async with websockets.connect(backend_uri) as ws:
            logger.info("Backend connected, proxying")

            # Send audio-start
            await ws.send(
                f'{{"type":"audio-start","data":{{"rate":{SAMPLE_RATE},"width":{SAMPLE_WIDTH},"channels":{CHANNELS},"mode":"streaming"}},"payload_length":0}}'
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
                    # Read frame header: [type:1][length:2]
                    hdr = await read_exact(reader, 3)
                    msg_type = hdr[0]
                    payload_len = struct.unpack("!H", hdr[1:3])[0]

                    payload = b""
                    if payload_len > 0:
                        payload = await read_exact(reader, payload_len)

                    if msg_type == MSG_AUDIO:
                        # Wyoming audio-chunk: JSON header then binary
                        header = f'{{"type":"audio-chunk","data":{{"rate":{SAMPLE_RATE},"width":{SAMPLE_WIDTH},"channels":{CHANNELS}}},"payload_length":{payload_len}}}'
                        await ws.send(header)
                        await ws.send(payload)

                    elif msg_type == MSG_BUTTON:
                        code = payload[0] if payload else 0
                        name = BUTTON_NAMES.get(code, f"UNKNOWN_{code}")
                        logger.info("Button: %s", name)
                        msg = f'{{"type":"button-event","data":{{"state":"{name}"}},"payload_length":0}}'
                        await ws.send(msg)

                    else:
                        logger.warning("Unknown message type: 0x%02x", msg_type)
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
        logger.info("Session ended")


async def main():
    global BACKEND_URL, BACKEND_WS_URL, AUTH_USERNAME, AUTH_PASSWORD, DEVICE_NAME, SAMPLE_RATE, SAMPLE_WIDTH, CHANNELS

    parser = argparse.ArgumentParser(
        description="HAVPE Relay - TCP to WebSocket bridge"
    )
    parser.add_argument("--port", type=int, default=8989)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--backend-url", type=str, default=BACKEND_URL)
    parser.add_argument("--backend-ws-url", type=str, default=BACKEND_WS_URL)
    parser.add_argument("--username", type=str, default=AUTH_USERNAME)
    parser.add_argument("--password", type=str, default=AUTH_PASSWORD)
    parser.add_argument("--device-name", type=str, default=DEVICE_NAME)
    parser.add_argument("--sample-rate", type=int, default=SAMPLE_RATE)
    parser.add_argument("--sample-width", type=int, default=SAMPLE_WIDTH)
    parser.add_argument("--channels", type=int, default=CHANNELS)
    parser.add_argument("-v", "--verbose", action="count", default=0)
    args = parser.parse_args()

    BACKEND_URL = args.backend_url
    BACKEND_WS_URL = args.backend_ws_url
    AUTH_USERNAME = args.username
    AUTH_PASSWORD = args.password
    DEVICE_NAME = args.device_name
    SAMPLE_RATE = args.sample_rate
    SAMPLE_WIDTH = args.sample_width
    CHANNELS = args.channels

    level = logging.WARNING - (10 * min(args.verbose, 2))
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=level)

    if not AUTH_USERNAME or not AUTH_PASSWORD:
        logger.error(
            "Set AUTH_USERNAME and AUTH_PASSWORD (env or --username/--password)"
        )
        return

    token = await get_jwt_token(AUTH_USERNAME, AUTH_PASSWORD, BACKEND_URL)
    if not token:
        logger.error("Startup auth check failed")
        return

    server = await asyncio.start_server(handle_device, args.host, args.port)
    logger.info("Relay listening on %s:%d (TCP)", args.host, args.port)
    logger.info("Backend: %s", BACKEND_URL)

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
