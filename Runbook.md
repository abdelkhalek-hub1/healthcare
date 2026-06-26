# Runbook — Healthcare AI Router

Operational runbook for SREs and platform engineers.

---

## Service Overview

| Service | Port | Technology | Health Check |
|---|---|---|---|
| Frontend | 3000 (Docker) / 5173 (dev) | React + Nginx | `GET /health.txt` |
| Backend | 8000 | FastAPI + Uvicorn | `GET /api/v1/health` |
| MongoDB | 27017 | MongoDB 7.0 | `mongosh ping` |

---

## Startup Procedures

### Start Full Stack (Docker)

```bash
# 1. Configure environment
cp .env.example .env
vi .env   # Set GROQ_API_KEY

# 2. Build and start all services
docker compose up --build -d

# 3. Verify all services are healthy
docker compose ps
docker compose logs backend --tail=50
```

### Start for Development

```bash
# MongoDB (local)
mongod --dbpath /data/db

# Backend
cd backend
source venv/bin/activate      # Linux/Mac
# or: venv\Scripts\activate   # Windows
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm run dev
```

---

## Health Checks

### API Health Endpoint

```bash
curl http://localhost:8000/api/v1/health | jq .
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "timestamp": "...",
  "services": {
    "mongodb": { "status": "healthy", "latency_ms": 2.1 },
    "groq": { "status": "healthy", "latency_ms": 340.5 }
  }
}
```

### Service Status Codes

| Status | Meaning |
|---|---|
| `healthy` | All checks passed |
| `degraded` | One or more services have elevated latency but are responsive |
| `unhealthy` | One or more services are unreachable |

---

## Common Operations

### View Live Logs

```bash
# Docker
docker compose logs -f backend

# Local (structured JSON logs)
uvicorn main:app --log-level info 2>&1 | python -m json.tool
```

### Run Database Maintenance

```bash
# Connect to MongoDB
docker compose exec mongodb mongosh healthcare_ai

# Count sessions
db.sessions.countDocuments()

# Recent telemetry
db.telemetry.find().sort({timestamp: -1}).limit(10)

# Drop test data
db.sessions.deleteMany({})
db.messages.deleteMany({})
db.telemetry.deleteMany({})
```

### Scale Backend (Docker)

```bash
# Run 3 backend replicas
docker compose up --scale backend=3 -d
```

---

## Incident Response

### Groq API Failures

**Symptoms:** `503 Service Unavailable` or high latency in telemetry

**Steps:**
1. Check Groq status: https://status.groq.com
2. Verify `GROQ_API_KEY` is valid
3. Check retry config: `GROQ_MAX_RETRIES` (default: 3)
4. Review backend logs for rate-limit errors (`429`)

**Escalation:** Increase `GROQ_TIMEOUT` and `GROQ_MAX_RETRIES` temporarily

---

### MongoDB Connection Issues

**Symptoms:** `503 Database Unavailable` in health endpoint

**Steps:**
1. Check MongoDB container: `docker compose ps mongodb`
2. Test connectivity: `docker compose exec mongodb mongosh --eval "db.ping()"`
3. Check `MONGODB_URL` matches the running instance
4. Review MongoDB logs: `docker compose logs mongodb`

---

### High Latency Alerts

**Symptoms:** `avg_latency_ms > 5000` in monitoring dashboard

**Steps:**
1. Open Monitoring page → check per-agent latency
2. If Groq is slow → reduce `GROQ_MAX_TOKENS`
3. If MongoDB is slow → check index coverage: `db.messages.getIndexes()`
4. Check for LangSmith tracing overhead: set `LANGCHAIN_TRACING_V2=false`

---

### LangGraph Graph Errors

**Symptoms:** `error` intent in telemetry, `intent=error` in router output

**Steps:**
1. Check `router_agent.py` prompt response parsing
2. Verify `GROQ_MODEL` model name is valid
3. Review graph trace if `LANGCHAIN_TRACING_V2=true`
4. Test router directly:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "session_id": null}'
```

---

## Rollback Procedure

```bash
# Tag current image before deploy
docker tag healthcare-ai-router-backend:latest healthcare-ai-router-backend:rollback

# Rollback
docker compose down
docker tag healthcare-ai-router-backend:rollback healthcare-ai-router-backend:latest
docker compose up -d
```

---

## Monitoring Queries

### Top Errors (last 24h)

```javascript
db.telemetry.aggregate([
  { $match: { status: "error", timestamp: { $gte: new Date(Date.now() - 86400000).toISOString() } } },
  { $group: { _id: "$error", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
])
```

### Average Latency per Agent

```javascript
db.telemetry.aggregate([
  { $group: { _id: "$selected_agent", avg_latency: { $avg: "$latency_ms" }, count: { $sum: 1 } } },
  { $sort: { avg_latency: -1 } }
])
```

---

## Backup & Restore

```bash
# Backup
docker compose exec mongodb mongodump --db healthcare_ai --out /tmp/backup
docker cp healthcare_mongodb:/tmp/backup ./backup

# Restore
docker cp ./backup healthcare_mongodb:/tmp/restore
docker compose exec mongodb mongorestore --db healthcare_ai /tmp/restore/healthcare_ai
```

---

## Contact & Escalation

| Tier | Responsibility | Response SLA |
|---|---|---|
| L1 | Service restart, log review | 15 min |
| L2 | Configuration changes, Groq/MongoDB issues | 30 min |
| L3 | Code changes, architecture review | 2 hours |
