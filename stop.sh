#!/bin/bash
source "$(dirname "$0")/scripts/check_uv.sh"
if [ $# -eq 0 ]; then
    uv run --with-requirements setup-requirements.txt python services.py stop --all
else
    uv run --with-requirements setup-requirements.txt python services.py stop "$@"
fi
