#!/usr/bin/env python3
"""
DAC Agent - Interactive Demo Dashboard
========================================

A standalone web-based dashboard for demonstrating the "Confused Deputy" attack
prevention in real-time. Perfect for sales demos, investor pitches, and technical
presentations.

Features:
- Real-time visualization of agent sessions
- Interactive attack simulation
- Token scope visualization
- Audit trail with color coding
- Session status monitoring
- No dependencies on Redis/Go/Docker

Usage:
    python demo_dashboard.py

Then open: http://localhost:3000
"""

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import hashlib
import time
import random

app = Flask(__name__)
CORS(app)

# Simulated state (in-memory)
STATE = {
    'sessions': {},
    'audit_logs': [],
    'tokens': {},
    'attack_in_progress': False,
    'container_status': 'RUNNING',
    'active_users': 1247
}

def generate_session_uuid(user_id):
    """Generate a session UUID."""
    timestamp = int(time.time())
    data = f"{user_id}:{timestamp}"
    hash_obj = hashlib.sha256(data.encode())
    return f"sess-{hash_obj.hexdigest()[:12]}"

def generate_token_id(user_id):
    """Generate a token ID."""
    hash_obj = hashlib.sha256(user_id.encode())
    return f"ASIA_{user_id.split('@')[0].upper()}_{hash_obj.hexdigest()[:12].upper()}"

def init_demo_state():
    """Initialize demo with Alice and Bob sessions."""
    # Alice's session
    alice_session_id = generate_session_uuid("alice@corp.com")
    STATE['sessions']['alice'] = {
        'user_id': 'alice@corp.com',
        'session_uuid': alice_session_id,
        'status': 'ACTIVE',
        'token_scope': 'arn:aws:s3:::data/alice/*',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'expires_at': (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
        'requests_count': 3,
        'bytes_used': 1024 * 45,  # 45 KB
        'violations': 0
    }

    STATE['tokens']['alice'] = {
        'token_id': generate_token_id('alice@corp.com'),
        'scope': 's3://data/alice/*',
        'expires_at': (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
        'type': 'USER_SCOPED'
    }

    # Bob's session
    bob_session_id = generate_session_uuid("bob@corp.com")
    STATE['sessions']['bob'] = {
        'user_id': 'bob@corp.com',
        'session_uuid': bob_session_id,
        'status': 'ACTIVE',
        'token_scope': 'arn:aws:s3:::data/bob/*',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'expires_at': (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
        'requests_count': 7,
        'bytes_used': 1024 * 120,  # 120 KB
        'violations': 0
    }

    STATE['tokens']['bob'] = {
        'token_id': generate_token_id('bob@corp.com'),
        'scope': 's3://data/bob/*',
        'expires_at': (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
        'type': 'USER_SCOPED'
    }

    # Initial audit logs (normal activity)
    STATE['audit_logs'] = [
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': 'alice@corp.com',
            'action': 'GET s3://data/alice/q4-report.pdf',
            'result': 'SUCCESS',
            'session': alice_session_id,
            'type': 'normal'
        },
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': 'bob@corp.com',
            'action': 'GET s3://data/bob/sales-metrics.xlsx',
            'result': 'SUCCESS',
            'session': bob_session_id,
            'type': 'normal'
        },
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': 'alice@corp.com',
            'action': 'GET s3://data/alice/contracts/acme.pdf',
            'result': 'SUCCESS',
            'session': alice_session_id,
            'type': 'normal'
        }
    ]

# Initialize on startup
init_demo_state()

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DAC Agent - Interactive Demo Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            min-height: 100vh;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(30, 41, 59, 0.5);
            border-radius: 12px;
            border: 1px solid #334155;
        }

        .header h1 {
            font-size: 2rem;
            color: #60a5fa;
            margin-bottom: 10px;
        }

        .header p {
            color: #94a3b8;
            font-size: 1rem;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s ease;
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
            border-color: #60a5fa;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #334155;
        }

        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #f1f5f9;
        }

        .status-badge {
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .status-active {
            background: #065f46;
            color: #6ee7b7;
        }

        .status-revoked {
            background: #7f1d1d;
            color: #fca5a5;
        }

        .status-warning {
            background: #92400e;
            color: #fbbf24;
        }

        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #334155;
        }

        .stat-row:last-child {
            border-bottom: none;
        }

        .stat-label {
            color: #94a3b8;
            font-size: 0.85rem;
        }

        .stat-value {
            color: #e2e8f0;
            font-weight: 500;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
        }

        .token-scope {
            background: #1e3a8a;
            color: #93c5fd;
            padding: 8px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 0.75rem;
            margin-top: 10px;
            word-break: break-all;
        }

        .control-panel {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .button-group {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.9rem;
        }

        .btn-attack {
            background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
            color: white;
        }

        .btn-attack:hover {
            background: linear-gradient(135deg, #b91c1c 0%, #7f1d1d 100%);
            transform: scale(1.05);
        }

        .btn-reset {
            background: #3b82f6;
            color: white;
        }

        .btn-reset:hover {
            background: #2563eb;
        }

        .btn-revoke {
            background: #dc2626;
            color: white;
        }

        .btn-revoke:hover {
            background: #b91c1c;
        }

        .audit-log {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 20px;
            max-height: 400px;
            overflow-y: auto;
        }

        .audit-entry {
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 6px;
            border-left: 4px solid;
            font-size: 0.85rem;
        }

        .audit-normal {
            background: rgba(5, 150, 105, 0.1);
            border-left-color: #10b981;
        }

        .audit-blocked {
            background: rgba(220, 38, 38, 0.1);
            border-left-color: #ef4444;
        }

        .audit-revoked {
            background: rgba(251, 146, 60, 0.1);
            border-left-color: #f59e0b;
        }

        .audit-time {
            color: #64748b;
            font-size: 0.75rem;
        }

        .audit-action {
            color: #e2e8f0;
            margin: 4px 0;
        }

        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid;
            display: none;
        }

        .alert-success {
            background: rgba(5, 150, 105, 0.1);
            border-left-color: #10b981;
            color: #6ee7b7;
        }

        .alert-danger {
            background: rgba(220, 38, 38, 0.1);
            border-left-color: #ef4444;
            color: #fca5a5;
        }

        .pulse {
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }

        @keyframes pulse {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: .5;
            }
        }

        .container-status {
            text-align: center;
            padding: 20px;
            background: rgba(30, 41, 59, 0.5);
            border-radius: 12px;
            border: 1px solid #334155;
            margin-bottom: 20px;
        }

        .container-status h3 {
            color: #94a3b8;
            font-size: 0.9rem;
            margin-bottom: 10px;
        }

        .container-status .value {
            font-size: 2rem;
            font-weight: 700;
            color: #60a5fa;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ DAC Agent - Interactive Demo Dashboard</h1>
            <p>The "Confused Deputy" Attack Prevention - Live Simulation</p>
        </div>

        <div id="alert" class="alert"></div>

        <div class="container-status">
            <h3>AGENT CONTAINER STATUS</h3>
            <div class="value" id="container-status">RUNNING</div>
            <div style="color: #64748b; margin-top: 10px;">
                Active Users: <span id="active-users">1247</span> |
                Container: agent-container-prod-1
            </div>
        </div>

        <div class="control-panel">
            <div class="card-header">
                <h2 class="card-title">🎮 Demo Controls</h2>
            </div>
            <div class="button-group">
                <button class="btn btn-attack" onclick="simulateAttack()">
                    💀 Simulate Prompt Injection Attack (Alice → Bob's Data)
                </button>
                <button class="btn btn-reset" onclick="resetDemo()">
                    🔄 Reset Demo
                </button>
            </div>
        </div>

        <div class="grid">
            <!-- Alice's Session -->
            <div class="card" id="alice-card">
                <div class="card-header">
                    <h3 class="card-title">👤 Alice's Session</h3>
                    <span class="status-badge status-active" id="alice-status">ACTIVE</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">User ID</span>
                    <span class="stat-value" id="alice-user">alice@corp.com</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Session UUID</span>
                    <span class="stat-value" id="alice-session">Loading...</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Token ID</span>
                    <span class="stat-value" id="alice-token">Loading...</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Requests</span>
                    <span class="stat-value" id="alice-requests">0</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Data Usage</span>
                    <span class="stat-value" id="alice-usage">0 KB</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Violations</span>
                    <span class="stat-value" id="alice-violations">0</span>
                </div>
                <div class="token-scope">
                    🔐 Token Scope: <span id="alice-scope">s3://data/alice/*</span>
                </div>
            </div>

            <!-- Bob's Session -->
            <div class="card" id="bob-card">
                <div class="card-header">
                    <h3 class="card-title">👤 Bob's Session</h3>
                    <span class="status-badge status-active" id="bob-status">ACTIVE</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">User ID</span>
                    <span class="stat-value" id="bob-user">bob@corp.com</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Session UUID</span>
                    <span class="stat-value" id="bob-session">Loading...</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Token ID</span>
                    <span class="stat-value" id="bob-token">Loading...</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Requests</span>
                    <span class="stat-value" id="bob-requests">0</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Data Usage</span>
                    <span class="stat-value" id="bob-usage">0 KB</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Violations</span>
                    <span class="stat-value" id="bob-violations">0</span>
                </div>
                <div class="token-scope">
                    🔐 Token Scope: <span id="bob-scope">s3://data/bob/*</span>
                </div>
            </div>
        </div>

        <div class="audit-log">
            <div class="card-header">
                <h3 class="card-title">📝 Audit Trail (Real-Time)</h3>
            </div>
            <div id="audit-entries">
                <!-- Populated by JavaScript -->
            </div>
        </div>
    </div>

    <script>
        let updateInterval;

        function showAlert(message, type) {
            const alert = document.getElementById('alert');
            alert.className = `alert alert-${type}`;
            alert.textContent = message;
            alert.style.display = 'block';
            setTimeout(() => {
                alert.style.display = 'none';
            }, 5000);
        }

        async function updateDashboard() {
            try {
                const response = await fetch('/api/state');
                const data = await response.json();

                // Update Alice
                if (data.sessions.alice) {
                    const alice = data.sessions.alice;
                    document.getElementById('alice-session').textContent = alice.session_uuid;
                    document.getElementById('alice-requests').textContent = alice.requests_count;
                    document.getElementById('alice-usage').textContent = Math.round(alice.bytes_used / 1024) + ' KB';
                    document.getElementById('alice-violations').textContent = alice.violations;

                    const aliceStatus = document.getElementById('alice-status');
                    aliceStatus.textContent = alice.status;
                    aliceStatus.className = `status-badge ${alice.status === 'ACTIVE' ? 'status-active' : 'status-revoked'}`;

                    const aliceCard = document.getElementById('alice-card');
                    if (alice.status === 'REVOKED') {
                        aliceCard.style.opacity = '0.6';
                        aliceCard.style.border = '2px solid #dc2626';
                    }
                }

                // Update Bob
                if (data.sessions.bob) {
                    const bob = data.sessions.bob;
                    document.getElementById('bob-session').textContent = bob.session_uuid;
                    document.getElementById('bob-requests').textContent = bob.requests_count;
                    document.getElementById('bob-usage').textContent = Math.round(bob.bytes_used / 1024) + ' KB';
                    document.getElementById('bob-violations').textContent = bob.violations;
                }

                // Update tokens
                if (data.tokens.alice) {
                    document.getElementById('alice-token').textContent = data.tokens.alice.token_id;
                }
                if (data.tokens.bob) {
                    document.getElementById('bob-token').textContent = data.tokens.bob.token_id;
                }

                // Update audit log
                const auditContainer = document.getElementById('audit-entries');
                auditContainer.innerHTML = '';

                data.audit_logs.slice().reverse().forEach(log => {
                    const entry = document.createElement('div');
                    entry.className = `audit-entry audit-${log.type}`;
                    entry.innerHTML = `
                        <div class="audit-time">${log.timestamp}</div>
                        <div class="audit-action"><strong>${log.user}</strong> - ${log.action}</div>
                        <div style="color: #64748b; font-size: 0.75rem;">
                            Result: ${log.result} | Session: ${log.session.substring(0, 20)}...
                        </div>
                    `;
                    auditContainer.appendChild(entry);
                });

                // Update container status
                document.getElementById('active-users').textContent = data.active_users;

            } catch (error) {
                console.error('Error updating dashboard:', error);
            }
        }

        async function simulateAttack() {
            try {
                showAlert('🚨 SIMULATING ATTACK: Alice attempting to access Bob\'s data via prompt injection...', 'danger');

                const response = await fetch('/api/attack', { method: 'POST' });
                const data = await response.json();

                if (data.blocked) {
                    setTimeout(() => {
                        showAlert('✅ ATTACK BLOCKED: Alice\'s token scope prevented access to Bob\'s resources!', 'success');
                    }, 2000);

                    setTimeout(() => {
                        showAlert('🔪 SURGICAL REVOCATION: Alice\'s session terminated. Bob and 1,245 other users continue normally.', 'success');
                    }, 4000);
                }

                updateDashboard();
            } catch (error) {
                console.error('Error simulating attack:', error);
            }
        }

        async function resetDemo() {
            try {
                await fetch('/api/reset', { method: 'POST' });
                showAlert('🔄 Demo reset successfully', 'success');
                updateDashboard();
            } catch (error) {
                console.error('Error resetting demo:', error);
            }
        }

        // Initial load and set up auto-refresh
        updateDashboard();
        updateInterval = setInterval(updateDashboard, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the dashboard."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/state')
def get_state():
    """Get current state."""
    return jsonify(STATE)

@app.route('/api/attack', methods=['POST'])
def simulate_attack():
    """Simulate the Confused Deputy attack."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    alice_session = STATE['sessions']['alice']['session_uuid']

    # Log the attack attempt
    STATE['audit_logs'].append({
        'timestamp': timestamp,
        'user': 'alice@corp.com',
        'action': 'GET s3://data/bob/q4-financials.pdf',
        'result': 'BLOCKED (Token Scope Violation)',
        'session': alice_session,
        'type': 'blocked'
    })

    # Increment violation count
    STATE['sessions']['alice']['violations'] += 1
    STATE['sessions']['alice']['requests_count'] += 1

    # Revoke Alice's session after violation
    STATE['sessions']['alice']['status'] = 'REVOKED'

    # Log revocation
    STATE['audit_logs'].append({
        'timestamp': timestamp,
        'user': 'SYSTEM',
        'action': f'SESSION REVOKED: {alice_session} (Unauthorized access attempt)',
        'result': 'REVOKED',
        'session': alice_session,
        'type': 'revoked'
    })

    # Decrement active users
    STATE['active_users'] -= 1

    return jsonify({
        'blocked': True,
        'reason': 'Token scope violation',
        'session_revoked': True
    })

@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset the demo to initial state."""
    global STATE
    STATE = {
        'sessions': {},
        'audit_logs': [],
        'tokens': {},
        'attack_in_progress': False,
        'container_status': 'RUNNING',
        'active_users': 1247
    }
    init_demo_state()
    return jsonify({'success': True})

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🚀 DAC Agent - Interactive Demo Dashboard")
    print("=" * 80)
    print("\n📊 Dashboard Features:")
    print("  • Real-time session monitoring")
    print("  • Interactive attack simulation")
    print("  • Token scope visualization")
    print("  • Live audit trail")
    print("  • Surgical revocation demo")
    print("\n🌐 Access the dashboard at:")
    print("  http://localhost:3000")
    print("\n💡 Demo Instructions:")
    print("  1. Click 'Simulate Prompt Injection Attack' to see the attack")
    print("  2. Watch Alice's session get blocked and revoked")
    print("  3. Notice Bob's session continues unaffected")
    print("  4. Check the audit trail for complete attribution")
    print("  5. Click 'Reset Demo' to start over")
    print("\n" + "=" * 80 + "\n")

    app.run(debug=False, host='0.0.0.0', port=3000)
