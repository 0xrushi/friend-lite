/**
 * chronicle.h - Wyoming protocol TCP client for Chronicle relay.
 *
 * Sends Wyoming-formatted messages over TCP (JSONL + binary payload).
 * The relay forwards them to the backend WebSocket as-is.
 *
 * Wire format per message:
 *   JSON line terminated by \n
 *   If payload_length > 0: raw binary bytes follow
 *
 * All functions are safe to call from ESPHome lambdas.
 */
#pragma once

#include <cstdio>
#include <cstring>
#include "esp_log.h"
#include <lwip/sockets.h>
#include <lwip/inet.h>

namespace chronicle {

static const char* TAG = "chronicle";

static int sockfd = -1;
static bool connected = false;

// Scratch buffer for JSON lines (256 bytes is plenty for Wyoming headers)
static char json_buf[256];

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

// ── internal: send all bytes reliably ───────────────────────────
static bool send_all(const void* data, size_t len) {
    if (sockfd < 0) return false;
    const uint8_t* p = (const uint8_t*)data;
    size_t sent = 0;
    while (sent < len) {
        ssize_t n = lwip_send(sockfd, p + sent, len - sent, 0);
        if (n <= 0) { disconnect(); return false; }
        sent += n;
    }
    return true;
}

// ── audio-start: call once after connect ────────────────────────
bool send_audio_start(int rate, int width, int channels, const char* mode = "streaming") {
    int n = snprintf(json_buf, sizeof(json_buf),
        "{\"type\":\"audio-start\",\"data\":{\"rate\":%d,\"width\":%d,\"channels\":%d,\"mode\":\"%s\"},\"payload_length\":0}\n",
        rate, width, channels, mode);
    return send_all(json_buf, n);
}

// ── audio-chunk: JSON line + binary payload ─────────────────────
bool send_audio(const uint8_t* pcm, size_t len, int rate, int width, int channels) {
    int n = snprintf(json_buf, sizeof(json_buf),
        "{\"type\":\"audio-chunk\",\"data\":{\"rate\":%d,\"width\":%d,\"channels\":%d},\"payload_length\":%u}\n",
        rate, width, channels, (unsigned)len);
    if (!send_all(json_buf, n)) return false;
    return send_all(pcm, len);
}

// ── audio-stop: signal end of session ───────────────────────────
bool send_audio_stop() {
    int n = snprintf(json_buf, sizeof(json_buf),
        "{\"type\":\"audio-stop\",\"data\":{},\"payload_length\":0}\n");
    return send_all(json_buf, n);
}

// ── button event ────────────────────────────────────────────────
// state: "SINGLE_PRESS", "DOUBLE_PRESS", "LONG_PRESS"
bool send_button(const char* state) {
    ESP_LOGI(TAG, "Sending button %s", state);
    int n = snprintf(json_buf, sizeof(json_buf),
        "{\"type\":\"button-event\",\"data\":{\"state\":\"%s\"},\"payload_length\":0}\n",
        state);
    return send_all(json_buf, n);
}

}  // namespace chronicle
