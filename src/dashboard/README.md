# Enterprise Dashboard

The **Unified View** dashboard for Agentic AI Identity Management.

## Features

### 📊 Real-Time Monitoring
- **Total Agents**: Count of registered DIDs
- **Active Sessions**: Currently running agent sessions
- **ANS Registrations**: Discoverable agents
- **Events (24h)**: Recent audit log activity

### 🤖 Agent Management
- View all registered agents
- Inspect DIDs and capabilities
- Track agent models and providers

### 🔒 Session Management
- Monitor active sessions
- **Surgical Kill Switch**: Revoke individual sessions instantly
- View session expiration times
- Track session capabilities

### 📝 Audit Trail
- Complete attribution of all actions
- DID-based event tracking
- Filterable event logs
- Non-repudiable audit records

### 🌐 ANS Registry Browser
- Browse all registered agents
- Search by capability
- View service endpoints
- Provider and version tracking

### ☁️ Cloud Credential Tracking
- Monitor cached AWS/GCP credentials
- View expiration times
- Track credential usage

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Dashboard
```bash
python src/dashboard/app.py
```

### 3. Access the Dashboard
Open your browser to: **http://localhost:5000**

## API Endpoints

The dashboard exposes the following REST API:

- `GET /api/stats` - Overall system statistics
- `GET /api/agents` - List all registered agents
- `GET /api/sessions` - List active sessions
- `POST /api/sessions/<id>/revoke` - Revoke a session
- `GET /api/audit-logs` - Fetch audit trail
- `GET /api/ans/registry` - ANS registry entries
- `GET /api/cloud-credentials` - Cached cloud credentials

## Security Features

### Surgical Kill Switch
Click "Revoke" next to any active session to instantly terminate it. This creates an audit log entry and prevents the agent from making further requests.

### Complete Attribution
Every event in the audit log is tied to a specific agent DID, providing non-repudiable proof of actions.

### Real-Time Updates
Statistics refresh automatically every 5 seconds to provide up-to-date visibility.

## Production Deployment

For production use:

1. **Enable Authentication**: Add OAuth/OIDC for dashboard access
2. **HTTPS**: Use a reverse proxy (nginx, Caddy)
3. **Scale Backend**: Replace in-memory SessionAuthority with Redis
4. **Monitoring**: Integrate with Prometheus/Grafana
5. **Alerts**: Configure webhooks for critical events

### Example Production Stack

```yaml
# docker-compose.yml
version: '3.8'
services:
  dashboard:
    build: .
    ports:
      - "5000:5000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:5432/agents
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: agents
    volumes:
      - postgres-data:/var/lib/postgresql/data
```

## Screenshots

The dashboard provides:
- **Dark mode UI** optimized for SOC teams
- **Real-time statistics** with auto-refresh
- **Tabbed interface** for different views
- **Responsive design** for desktop and tablet

## Integration with Enterprise Demo

The dashboard complements the `demo_enterprise.py` by providing:
1. Visual confirmation of agent registrations
2. Real-time session monitoring
3. Audit trail verification
4. Cloud credential cache inspection

Run the enterprise demo, then view the results in the dashboard to see the complete system in action.
