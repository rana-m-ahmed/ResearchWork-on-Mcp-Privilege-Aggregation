#!/bin/bash
# Check Docker compose file for safety baseline

COMPOSE_FILE="docker/docker-compose.phase2.yml"

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "ERROR: $COMPOSE_FILE not found!"
    exit 1
fi

echo "Checking Docker safety baseline in $COMPOSE_FILE..."

# Must fail if it detects privileged: true
if grep -q "privileged: true" "$COMPOSE_FILE"; then
    echo "FAIL: Found 'privileged: true'"
    exit 1
fi

# Must fail if it detects network_mode: host
if grep -q "network_mode: host" "$COMPOSE_FILE"; then
    echo "FAIL: Found 'network_mode: host'"
    exit 1
fi

# Must fail if it detects a repo-root writable mount, parent-directory mount,
# /root mount, /home mount, or broad host filesystem exposure.
# Check for simple string patterns in volumes mapping.

if grep -E "^[[:space:]]*- \.:" "$COMPOSE_FILE" >/dev/null 2>&1; then
    echo "FAIL: Found repo-root bind mount"
    exit 1
fi

if grep -E "^[[:space:]]*- \.\.:" "$COMPOSE_FILE" >/dev/null 2>&1; then
    echo "FAIL: Found parent-directory bind mount"
    exit 1
fi

if grep -q "/root:" "$COMPOSE_FILE" || grep -q "/home:" "$COMPOSE_FILE"; then
    echo "FAIL: Found /root or /home bind mount"
    exit 1
fi

if grep -E "^[[:space:]]*- /:" "$COMPOSE_FILE" >/dev/null 2>&1; then
    echo "FAIL: Found broad host filesystem mount (/)"
    exit 1
fi

echo "PASS: Docker safety baseline checks completed successfully."
exit 0
