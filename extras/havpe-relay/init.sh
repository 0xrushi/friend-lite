#!/bin/bash
source "$(dirname "$0")/../../scripts/check_uv.sh"
uv run --no-project --with-requirements ../../setup-requirements.txt python init.py "$@"
