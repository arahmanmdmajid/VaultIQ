#!/bin/bash
set -e
cd "$(dirname "$0")"

echo
echo " *** VaultIQ — Lobster Trap AI Governance Proxy ***"
echo " Routing: Streamlit app -> Lobster Trap (:8080) -> Groq API"
echo

if [ ! -f "./lobstertrap" ]; then
    echo " [ERROR] ./lobstertrap binary not found."
    echo
    echo " Build from source (requires Go 1.22+):"
    echo "   git clone https://github.com/veeainc/lobstertrap /tmp/lt"
    echo "   cd /tmp/lt && make build"
    echo "   cp lobstertrap $(pwd)/"
    echo
    exit 1
fi

echo " Policy   : policy.yaml"
echo " Audit    : audit.jsonl"
echo " Listen   : http://localhost:8080"
echo " Backend  : https://api.groq.com/openai/v1"
echo " Dashboard: http://localhost:8080/_lobstertrap/"
echo
echo " Press Ctrl+C to stop."
echo

./lobstertrap serve \
    --backend https://api.groq.com/openai/v1 \
    --listen :8080 \
    --policy policy.yaml \
    --audit-log audit.jsonl
