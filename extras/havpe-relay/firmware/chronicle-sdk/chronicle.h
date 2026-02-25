/**
 * chronicle.h - Minimal TCP client for streaming to Chronicle relay.
 *
 * Sends framed messages over TCP: [type:1][length:2][payload]
 * The relay handles Wyoming protocol + WebSocket + auth.
 *
 * All functions are safe to call from ESPHome lambdas.
 */
#pragma once

#include <cstring>
#include "esp_log.h"
#include <lwip/sockets.h>
#include <lwip/inet.h>

namespace chronicle {

static const char* TAG = "chronicle";

static int sockfd = -1;
static bool connected = false;

// Message types
static const uint8_t MSG_AUDIO  = 0x01;
static const uint8_t MSG_BUTTON = 0x02;

// Button codes
static const uint8_t BTN_SINGLE = 0x01;
static const uint8_t BTN_DOUBLE = 0x02;
static const uint8_t BTN_LONG   = 0x03;

// ── connect to relay ────────────────────────────────────────────
bool connect_relay(const char* ip, int port) {
    sockfd = lwip_socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        ESP_LOGE(TAG, "socket() failed");
        return false;
    }

    struct timeval tv = {.tv_sec = 5, .tv_usec = 0};
    lwip_setsockopt(sockfd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

    struct sockaddr_in dest = {};
    dest.sin_family = AF_INET;
    dest.sin_port = htons(port);
    inet_pton(AF_INET, ip, &dest.sin_addr);

    if (lwip_connect(sockfd, (struct sockaddr*)&dest, sizeof(dest)) < 0) {
        ESP_LOGW(TAG, "connect to %s:%d failed errno=%d", ip, port, errno);
        lwip_close(sockfd);
        sockfd = -1;
        return false;
    }

    connected = true;
    ESP_LOGI(TAG, "TCP connected to relay %s:%d", ip, port);
    return true;
}

bool is_connected() { return connected && sockfd >= 0; }

void disconnect() {
    if (sockfd >= 0) lwip_close(sockfd);
    sockfd = -1;
    connected = false;
}

// ── send framed message: [type:1][length:2 big-endian][payload] ─
static bool send_msg(uint8_t type, const uint8_t* data, uint16_t len) {
    if (sockfd < 0) return false;
    uint8_t hdr[3] = {type, (uint8_t)(len >> 8), (uint8_t)(len & 0xFF)};
    if (lwip_send(sockfd, hdr, 3, 0) != 3) { disconnect(); return false; }
    if (len > 0) {
        size_t sent = 0;
        while (sent < len) {
            ssize_t n = lwip_send(sockfd, data + sent, len - sent, 0);
            if (n <= 0) { disconnect(); return false; }
            sent += n;
        }
    }
    return true;
}

// ── audio: split into 65535-byte chunks if needed ───────────────
bool send_audio(const uint8_t* pcm, size_t len) {
    while (len > 0) {
        uint16_t chunk = len > 65535 ? 65535 : (uint16_t)len;
        if (!send_msg(MSG_AUDIO, pcm, chunk)) return false;
        pcm += chunk;
        len -= chunk;
    }
    return true;
}

// ── button ──────────────────────────────────────────────────────
bool send_button(uint8_t code) {
    ESP_LOGI(TAG, "Sending button %d", code);
    return send_msg(MSG_BUTTON, &code, 1);
}

}  // namespace chronicle
