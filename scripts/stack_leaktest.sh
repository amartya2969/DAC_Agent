#!/usr/bin/env bash
# Run the framework leak test (LangChain, LlamaIndex, Mem0) against Qdrant,
# directly and through the DAC sidecar.
#
#   pip install -r tools/leaktest/requirements-stacks.txt
#   ./scripts/stack_leaktest.sh
#
# Uses Qdrant at QDRANT_URL (default http://127.0.0.1:6333), starting the
# qdrant/qdrant Docker image if nothing is listening there. Starts one sidecar
# per framework, since each stores the tenant under a different payload key.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:6333}"
OUT="${OUT:-$ROOT/leaktest-output}"
mkdir -p "$OUT"
WORK="$(mktemp -d)"
PIDS=()
CONTAINER=""

cleanup() {
    for pid in "${PIDS[@]:-}"; do
        [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
    done
    [ -n "$CONTAINER" ] && docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    rm -rf "$WORK"
}
trap cleanup EXIT

wait_for() {
    for _ in $(seq 1 60); do
        curl -sf "$1" >/dev/null 2>&1 && return 0
        sleep 0.5
    done
    echo "Timed out waiting for $1" >&2
    return 1
}

"$PYTHON" -c "import langchain_qdrant, llama_index.vector_stores.qdrant, mem0" 2>/dev/null || {
    echo "Framework packages missing: $PYTHON -m pip install -r $ROOT/tools/leaktest/requirements-stacks.txt" >&2
    exit 1
}

if ! curl -sf "$QDRANT_URL/" >/dev/null 2>&1; then
    echo "Starting qdrant/qdrant on $QDRANT_URL"
    CONTAINER="dac-leaktest-qdrant"
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    docker run -d --name "$CONTAINER" -p 6333:6333 qdrant/qdrant >/dev/null
    QDRANT_URL="http://127.0.0.1:6333"
fi
wait_for "$QDRANT_URL/"
echo "Qdrant $(curl -s "$QDRANT_URL/" | "$PYTHON" -c 'import json,sys; print(json.load(sys.stdin)["version"])') at $QDRANT_URL"

echo "Building sidecar..."
(cd "$ROOT/sidecar" && go build -o "$WORK/dac-sidecar" .)

SIDECAR_ARGS=()
port=18081
for pair in langchain=metadata.tenant_id llamaindex=tenant_id mem0=user_id; do
    stack="${pair%%=*}"
    key="${pair#*=}"
    VECTOR_STORE_URL="$QDRANT_URL" VECTOR_TENANT_KEY="$key" PROXY_PORT="$port" REDIS_URL="127.0.0.1:1" \
        "$WORK/dac-sidecar" >"$OUT/audit-$stack.jsonl" 2>"$OUT/sidecar-$stack.log" &
    PIDS+=($!)
    wait_for "http://127.0.0.1:$port/health"
    SIDECAR_ARGS+=(--sidecar "$stack=http://127.0.0.1:$port")
    port=$((port + 1))
done

"$PYTHON" "$ROOT/tools/leaktest/stacks.py" --store-url "$QDRANT_URL" "${SIDECAR_ARGS[@]}" \
    --report "$OUT/stacks-report.md" --json "$OUT/stacks-results.json" 2>&1 \
    | grep -v -iE "spacy|fastembed|deprecat"
STATUS=${PIPESTATUS[0]}

echo
echo "Outputs in $OUT: stacks-report.md, stacks-results.json, audit-*.jsonl"
exit "$STATUS"
