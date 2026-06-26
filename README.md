# Healthcare AI Router — Multi-Agent AI Healthcare System

<div align="center">

![Healthcare AI Router Banner](https://img.shields.io/badge/Healthcare%20AI-Router%20Pattern-0e94eb?style=for-the-badge&logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-7c3aed?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge&logo=react)
![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47a248?style=for-the-badge&logo=mongodb)
![Groq](https://img.shields.io/badge/Groq-LLaMA3-f55036?style=for-the-badge)

**Enterprise-grade AI Healthcare Assistant built on the LangGraph Router Pattern**

</div>

---

## Overview

The **Healthcare AI Router** is a production-ready, multi-agent AI system that classifies incoming patient queries and routes them to the appropriate specialized AI agent. Every request is traced, persisted, and monitored in real-time.

### Architecture: Router Pattern

```
User → FastAPI → Session Manager → LangGraph Router → Specialized Agent → Response
                                         ↓
                                   intent classification
                                   (confidence score)
                                         ↓
                     ┌─────────────────────────────────────────┐
                     │  Consultation │ Reimbursement │ FAQ      │
                     │  Follow-up   │ Error Handler │          │
                     └─────────────────────────────────────────┘
                                         ↓
                               Monitoring Node
                                         ↓
                                    MongoDB
```

---

## Features

| Feature | Description |
|---|---|
| 🔀 **LangGraph Router** | StateGraph with conditional edges — no if/else routing |
| 🤖 **4 Specialized Agents** | Consultation, Reimbursement, Follow-up, FAQ |
| 🧠 **Groq LLM** | LLaMA3-8B via Groq API with exponential backoff retries |
| 📦 **Structured Outputs** | Every agent returns Pydantic-validated JSON schemas |
| 🗄️ **MongoDB Persistence** | Sessions, messages, telemetry, and feedback |
| 📊 **Real-time Monitoring** | Latency, token usage, agent routing per request |
| 🔍 **LangSmith Tracing** | Optional trace forwarding for debugging |
| 🌐 **React Frontend** | Dark/light mode, live chat, history browser, telemetry UI |
| 🐳 **Docker Ready** | Multi-stage Dockerfiles + full Compose stack |
| ✅ **21 Passing Tests** | pytest suite with mongomock, async fixtures |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Groq (`llama3-8b-8192`) |
| **Orchestration** | LangGraph `StateGraph` |
| **Backend** | FastAPI + Uvicorn |
| **Database** | MongoDB via Motor (async) |
| **Config** | `pydantic-settings` |
| **Frontend** | React 18 + Vite + TypeScript + TailwindCSS |
| **Containerization** | Docker + Docker Compose |
| **CI/CD** | GitHub Actions |

---

## Project Structure

```
.
├── backend/
│   ├── agents/              # Specialized AI agents
│   │   ├── router_agent.py
│   │   ├── consultation_agent.py
│   │   ├── reimbursement_agent.py
│   │   ├── followup_agent.py
│   │   ├── faq_agent.py
│   │   └── monitoring_agent.py
│   ├── api/
│   │   └── routes.py        # FastAPI endpoints
│   ├── database/
│   │   ├── connection.py    # Motor async client
│   │   └── repository.py   # Repository pattern
│   ├── graph/
│   │   ├── state.py         # GraphState TypedDict
│   │   └── graph_builder.py # LangGraph StateGraph
│   ├── middleware/          # CORS, correlation, timing, error handling
│   ├── models/              # Domain models
│   ├── prompts/             # File-based prompt repository
│   ├── schemas/             # Pydantic input/output schemas
│   ├── services/
│   │   ├── groq_service.py  # LLM factory with retry
│   │   ├── llm_factory.py
│   │   └── session_manager.py
│   ├── tests/               # Full pytest suite
│   ├── config.py            # pydantic-settings configuration
│   ├── main.py              # FastAPI app entrypoint
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/      # Reusable UI components
│       ├── context/         # AppContext (sessions, theme)
│       ├── hooks/           # useChat, useHealth, useMonitoring
│       ├── pages/           # 6 full pages
│       ├── services/        # API client (Axios)
│       └── types/           # TypeScript interfaces
├── docker-compose.yml
├── .env.example
└── .github/workflows/ci.yml
```

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Node.js 20+
- MongoDB 7.0 (local or Docker)
- [Groq API Key](https://console.groq.com)

### 2. Clone & Configure

```bash
git clone <repo-url>
cd healthcare-ai-router
cp .env.example .env
# Edit .env and set GROQ_API_KEY
```

### 3. Run with Docker Compose (recommended)

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

### 4. Run Locally (development)

**Backend:**
```bash
cd backend
python -m venv venv && venv\Scripts\activate     # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

**Tests:**
```bash
cd backend
pytest tests/ -v
```

---

## API Reference

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/chat` | Send a message, get AI response |
| `POST` | `/api/v1/feedback` | Submit thumbs up/down rating |

**Chat Request:**
```json
{
  "message": "I need to schedule a cardiology appointment",
  "session_id": null
}
```

**Chat Response:**
```json
{
  "session_id": "uuid",
  "correlation_id": "uuid",
  "intent": "consultation",
  "agent": "consultation_agent",
  "answer": "I can help you schedule...",
  "data": { "specialty": "cardiology", ... },
  "token_usage": { "total_tokens": 420 },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Sessions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/sessions` | List recent sessions |
| `GET` | `/api/v1/sessions/{id}` | Session detail |
| `GET` | `/api/v1/sessions/{id}/history` | Message history |

### Monitoring

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/monitoring` | Execution logs |
| `GET` | `/api/v1/monitoring/metrics` | Aggregate metrics |
| `GET` | `/api/v1/monitoring/agents` | Per-agent breakdown |
| `GET` | `/api/v1/health` | System health check |

---

## Intent Classification

| Intent | Agent | Use Case |
|---|---|---|
| `consultation` | `consultation_agent` | Appointment scheduling |
| `reimbursement` | `reimbursement_agent` | Insurance claims & coverage |
| `followup` | `followup_agent` | Symptom tracking & care advice |
| `faq` | `faq_agent` | General health questions |
| `error` | — | Routing failures |

---

## Environment Variables

See [`.env.example`](.env.example) for the complete list. Required:

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key |
| `MONGODB_URL` | MongoDB connection string |
| `MONGO_DB_NAME` | Database name |

---

## License

MIT
