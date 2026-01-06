"""Enterprise Dashboard - Unified View for Agentic AI Identity Management.

This provides:
1. Real-time agent monitoring
2. Session management and revocation
3. Audit log viewer with DID attribution
4. VC/DID registry browser
5. Cloud credential usage tracking
6. Policy enforcement status

The "SOC2 Dashboard" for enterprise compliance teams.
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.identity.did_manager import DIDManager
from src.identity.vc_issuer import VCIssuer
from src.ans.registry import ANSRegistry
from src.session.authority import SessionAuthority
from src.models.database import SessionLocal
from src.models.audit_log import AuditLog
from src.cloud.identity_bridge import CloudIdentityBridge, CloudCredentialCache

app = Flask(__name__)
CORS(app)

# Initialize components
did_manager = DIDManager()
vc_issuer = VCIssuer(did_manager=did_manager)
ans_registry = ANSRegistry()
cloud_bridge = CloudIdentityBridge(vc_issuer=vc_issuer)
credential_cache = CloudCredentialCache()

# In-memory session authority (in production, use Redis)
session_authority = SessionAuthority(redis_url=None)


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/stats')
def get_stats():
    """Get overall system statistics."""
    try:
        # Count DIDs
        did_files = len([f for f in os.listdir('data/dids') if f.endswith('.json')])

        # Count active sessions
        active_sessions = len([s for s in session_authority.sessions.values()
                              if s['status'] == 'ACTIVE'])

        # Count ANS registrations
        ans_entries = len(ans_registry.list_all())

        # Get audit log count
        db = SessionLocal()
        total_events = db.query(AuditLog).count()
        recent_events = db.query(AuditLog).filter(
            AuditLog.timestamp > (datetime.utcnow() - timedelta(hours=24))
        ).count()
        db.close()

        return jsonify({
            'total_agents': did_files,
            'active_sessions': active_sessions,
            'ans_registrations': ans_entries,
            'total_events': total_events,
            'events_24h': recent_events,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agents')
def get_agents():
    """List all registered agents."""
    try:
        agents = []
        did_dir = 'data/dids'

        if os.path.exists(did_dir):
            for filename in os.listdir(did_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(did_dir, filename)
                    with open(filepath, 'r') as f:
                        did_doc = json.load(f)

                        # Extract metadata
                        agent_info = {
                            'did': did_doc.get('id', 'Unknown'),
                            'name': did_doc.get('agentMetadata', {}).get('name', 'Unknown'),
                            'model': did_doc.get('agentMetadata', {}).get('model', 'Unknown'),
                            'provider': did_doc.get('agentMetadata', {}).get('provider', 'Unknown'),
                            'capabilities': did_doc.get('agentMetadata', {}).get('capabilities', []),
                            'created': did_doc.get('created', 'Unknown'),
                            'updated': did_doc.get('updated', 'Unknown')
                        }
                        agents.append(agent_info)

        return jsonify({'agents': agents})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions')
def get_sessions():
    """List all active sessions."""
    try:
        sessions_list = []

        for session_id, session_data in session_authority.sessions.items():
            sessions_list.append({
                'session_id': session_id,
                'agent_did': session_data.get('agent_did', 'Unknown')[:60] + '...',
                'status': session_data.get('status', 'UNKNOWN'),
                'created_at': session_data.get('created_at', 'Unknown'),
                'expires_at': session_data.get('expires_at', 'Unknown'),
                'capabilities': session_data.get('capabilities', [])
            })

        return jsonify({'sessions': sessions_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<session_id>/revoke', methods=['POST'])
def revoke_session(session_id):
    """Revoke a specific session (Surgical Kill Switch)."""
    try:
        result = session_authority.revoke_session(session_id)

        if result:
            # Log the revocation
            db = SessionLocal()
            audit_entry = AuditLog(
                event_type='SESSION_REVOKED',
                agent_did='ADMIN',
                session_id=session_id,
                resource='session_authority',
                action='revoke',
                result='SUCCESS',
                event_metadata=json.dumps({'reason': 'manual_revocation_via_dashboard'})
            )
            db.add(audit_entry)
            db.commit()
            db.close()

            return jsonify({'success': True, 'message': f'Session {session_id} revoked'})
        else:
            return jsonify({'success': False, 'message': 'Session not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/audit-logs')
def get_audit_logs():
    """Get recent audit logs."""
    try:
        limit = request.args.get('limit', 100, type=int)

        db = SessionLocal()
        logs = db.query(AuditLog)\
            .order_by(AuditLog.timestamp.desc())\
            .limit(limit)\
            .all()

        audit_data = []
        for log in logs:
            audit_data.append({
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'event_type': log.event_type,
                'agent_did': log.agent_did[:60] + '...' if log.agent_did else 'N/A',
                'session_id': log.session_id[:16] + '...' if log.session_id else 'N/A',
                'resource': log.resource,
                'action': log.action,
                'result': log.result,
                'metadata': log.event_metadata
            })

        db.close()
        return jsonify({'logs': audit_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ans/registry')
def get_ans_registry():
    """Get all ANS registrations."""
    try:
        entries = ans_registry.list_all()

        ans_data = []
        for entry in entries:
            ans_data.append({
                'ans_name': entry['ans_name'],
                'agent_did': entry['agent_did'][:60] + '...',
                'capabilities': entry['capabilities'],
                'service_endpoint': entry['service_endpoint'],
                'provider': entry['provider'],
                'version': entry['version'],
                'registered_at': entry['registered_at']
            })

        return jsonify({'entries': ans_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cloud-credentials')
def get_cloud_credentials():
    """Get cached cloud credentials (sanitized)."""
    try:
        creds_data = []

        for cache_key, credentials in credential_cache.cache.items():
            # Sanitize sensitive data
            creds_data.append({
                'cache_key': cache_key,
                'access_key_id': credentials.get('AccessKeyId', 'N/A')[:20] + '...',
                'expires_at': credentials.get('Expiration', 'N/A'),
                'provider': 'AWS' if 'AccessKeyId' in credentials else 'GCP'
            })

        return jsonify({'credentials': creds_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search')
def search():
    """Search agents by DID or capability."""
    try:
        query = request.args.get('q', '')

        if not query:
            return jsonify({'results': []})

        results = []

        # Search by capability in ANS
        capability_matches = ans_registry.resolve_by_capability(query)
        for match in capability_matches:
            results.append({
                'type': 'capability',
                'ans_name': match['ans_name'],
                'agent_did': match['agent_did'][:60] + '...',
                'service_endpoint': match['service_endpoint']
            })

        # Search by ANS name
        name_match = ans_registry.resolve(query)
        if name_match:
            results.append({
                'type': 'ans_name',
                'ans_name': name_match['ans_name'],
                'agent_did': name_match['agent_did'][:60] + '...',
                'capabilities': name_match['capabilities']
            })

        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🚀 Enterprise Dashboard - Agentic AI Identity Management")
    print("=" * 80)
    print("\n📊 Dashboard Features:")
    print("  • Real-time agent monitoring")
    print("  • Session management (with surgical kill switch)")
    print("  • Complete audit trail viewer")
    print("  • ANS registry browser")
    print("  • Cloud credential usage tracking")
    print("\n🌐 Access the dashboard at:")
    print("  http://localhost:5000")
    print("\n" + "=" * 80 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
