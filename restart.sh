#!/bin/bash
if [ $# -eq 0 ]; then
    uv run --with-requirements setup-requirements.txt python services.py restart --all
else
    uv run --with-requirements setup-requirements.txt python services.py restart "$@"
fi