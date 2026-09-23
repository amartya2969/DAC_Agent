#!/usr/bin/env bash
# Memory isolation demo: run the cross-tenant leak test against a shared
# vector store, first directly and then through the DAC sidecar.
#
#   ./scripts/memory_isolation_demo.sh
#
# Starts a Qdrant-compatible test server (or uses a real Qdrant if
# QDRANT_URL is set), builds and starts the sidecar with the tenant guard,
# runs tools/leaktest/leaktest.py, and summarises the sidecar's audit log.
# Needs Go and Python 3 with qdrant-client (pip install -r tools/leaktest/requirements.txt).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STORE_PORT="${STORE_PORT:-16333}"
SIDECAR_PORT="${SIDECAR_PORT:-18080}"
OUT="${OUT:-$ROOT/leaktest-output}"
mkdir -p "$OUT"
WORK="$(mktemp -d)"
PIDS=()

cleanup() {
    for pid in "${PIDS[@]:-}"; do
        [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
    done
    rm -rf "$WORK"
}
trap cleanup EXIT

wait_for() {
    for _ in $(seq 1 50); do
        curl -sf "$1" >/dev/null 2>&1 && return 0
        sleep 0.2
    done
    echo "Timed out waiting for $1" >&2
    return 1
}

python3 -c "import qdrant_client" 2>/dev/null || {
    echo "qdrant-client is missing: pip install -r $ROOT/tools/leaktest/requirements.txt" >&2
    exit 1
}

if [ -n "${QDRANT_URL:-}" ]; then
    STORE_URL="$QDRANT_URL"
    echo "Using Qdrant at $STORE_URL"
else
    STORE_URL="http://127.0.0.1:$STORE_PORT"
    python3 "$ROOT/tools/leaktest/qdrant_test_server.py" --port "$STORE_PORT" >"$WORK/store.log" 2>&1 &
    PIDS+=($!)
    echo "Started Qdrant-compatible test server on $STORE_URL"
fi
wait_for "$STORE_URL/"

echo "Building sidecar..."
(cd "$ROOT/sidecar" && go build -o "$WORK/dac-sidecar" .)

# Redis is not needed for the tenant guard; point it at a closed port.
VECTOR_STORE_URL="$STORE_URL" PROXY_PORT="$SIDECAR_PORT" REDIS_URL="127.0.0.1:1" \
    "$WORK/dac-sidecar" >"$OUT/audit.jsonl" 2>"$OUT/sidecar.log" &
PIDS+=($!)
wait_for "http://127.0.0.1:$SIDECAR_PORT/health"
echo "Sidecar with tenant guard on http://127.0.0.1:$SIDECAR_PORT/vector"

set +e
python3 "$ROOT/tools/leaktest/leaktest.py" \
    --store-url "$STORE_URL" \
    --sidecar-url "http://127.0.0.1:$SIDECAR_PORT" \
    --report "$OUT/report.md" --json "$OUT/results.json"
STATUS=$?
set -e

echo
echo "Sidecar audit log (security events):"
python3 - "$OUT/audit.jsonl" <<'EOF'
import json, sys
for line in open(sys.argv[1]):
    if not line.startswith("{"):
        continue
    e = json.loads(line)
    if e["outcome"] in ("BLOCKED", "CONTAINED"):
        print(f'  {e["outcome"]:9} {e["user"]:<20} {e["intent"]:<14} {e.get("reason", "")[:90]}')
EOF

echo
echo "Outputs in $OUT: report.md, results.json, audit.jsonl, sidecar.log"
exit $STATUS
