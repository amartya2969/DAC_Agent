#!/bin/bash
# View structured audit logs from the DAC Sidecar
#
# This script demonstrates "Identity-First Observability" by showing
# real-time JSON audit logs with complete attribution.
#
# Usage:
#   ./scripts/view_audit_logs.sh
#
# Or with pretty printing:
#   ./scripts/view_audit_logs.sh | jq
#
# Or filter for specific events:
#   ./scripts/view_audit_logs.sh | jq 'select(.event=="SECURITY_ALERT")'

echo "═══════════════════════════════════════════════════════════════════════"
echo "  DAC SIDECAR - IDENTITY-FIRST OBSERVABILITY"
echo "  Real-Time Structured Audit Logs"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "Watching for audit events..."
echo "  🟢 TRAFFIC = Allowed requests"
echo "  🔴 SECURITY_ALERT = Blocked requests"
echo "  🟠 CIRCUIT_BREAK = Rate limit exceeded"
echo ""
echo "Press Ctrl+C to stop"
echo "─────────────────────────────────────────────────────────────────────"
echo ""

# Check if running in docker-compose
if docker-compose ps sidecar &>/dev/null; then
    # Use docker-compose logs
    docker-compose logs -f --tail=0 sidecar | grep -E '^\{.*\}$'
elif docker ps | grep -q dac-sidecar; then
    # Use docker logs directly
    docker logs -f dac-sidecar | grep -E '^\{.*\}$'
else
    echo "❌ Error: Sidecar container not running"
    echo ""
    echo "Start the sidecar with:"
    echo "  docker-compose up sidecar"
    echo ""
    echo "Or for local development:"
    echo "  cd sidecar && go run ."
    exit 1
fi
