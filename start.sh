#!/bin/bash
source "$(dirname "$0")/scripts/check_uv.sh"
if [ $# -eq 0 ]; then
    uv run --with-requirements setup-requirements.txt python services.py start --all --build
else
    uv run --with-requirements setup-requirements.txt python services.py start "$@"
fi
