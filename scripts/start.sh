#!/usr/bin/env bash
set -euo pipefail

export QGC_ADDRESS
QGC_ADDRESS=$(python -c 'import os,socket; print(socket.gethostbyname(os.environ.get("QGC_HOST", "host.docker.internal")))')
envsubst '${QGC_ADDRESS}' < /opt/sitl/router.conf.template > /tmp/router.conf

cleanup() {
    trap - TERM INT EXIT
    kill "${sitl_pid:-}" "${router_pid:-}" "${api_pid:-}" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup TERM INT EXIT

# ArduPilot's conventional Canberra simulation site, not the user's location.
arducopter --model quad --speedup 1 --home -35.363261,149.165230,584,353 \
    --defaults /opt/sitl/copter.parm --serial0 tcp:0 &
sitl_pid=$!

python - <<'PY'
import socket
import time
for attempt in range(100):
    try:
        with socket.create_connection(("127.0.0.1", 5760), timeout=0.2):
            break
    except OSError:
        time.sleep(0.1)
else:
    raise SystemExit("ArduPilot did not open TCP port 5760")
PY

echo "Routing simulator telemetry to QGroundControl at ${QGC_ADDRESS}:14550"
mavlink-routerd -c /tmp/router.conf &
router_pid=$!

python - <<'PY'
import socket
import time
for attempt in range(100):
    try:
        with socket.create_connection(("127.0.0.1", 5770), timeout=0.2):
            break
    except OSError:
        time.sleep(0.1)
else:
    raise SystemExit("MAVLink-router did not open TCP port 5770")
PY

uvicorn app.main:app --app-dir /opt/sitl --host 0.0.0.0 --port 8000 &
api_pid=$!
wait -n "$sitl_pid" "$router_pid" "$api_pid"
# A long-running component exiting unexpectedly should stop the container.
exit 1
