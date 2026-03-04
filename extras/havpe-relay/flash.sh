#!/bin/bash
# Flash ESPHome firmware to ESP32-S3 Voice-PE
# Usage: ./flash.sh [run|logs]
#   ./flash.sh        - compile and flash firmware
#   ./flash.sh logs   - view device logs over serial/WiFi

set -e
cd "$(dirname "$0")/firmware"

if [ ! -f secrets.yaml ]; then
    echo "Error: firmware/secrets.yaml not found."
    echo "Run ./init.sh and enable firmware setup, or:"
    echo "  cp secrets.template.yaml secrets.yaml"
    echo "  # then edit secrets.yaml with your WiFi and relay IP"
    exit 1
fi

ACTION="${1:-run}"
cd ..
exec uv run --group firmware esphome "$ACTION" firmware/voice-chronicle.yaml
