# Architecture Diagram — Healthcare AI Router

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           REACT FRONTEND (Vite + TypeScript + TailwindCSS)       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ ┌───────┐  │
│  │Dashboard │  │  Chat UI │  │ History  │  │Monitoring│  │ Health │ │Setting│  │
│  │          │  │          │  │ Viewer   │  │ & Logs   │  │ Status │ │  s    │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘ └───────┘  │
│  ┌───────────────────────────────────────────────────────────────────────────┐   │
│  │  AppContext (sessions, theme)  │  useChat  │  useMonitoring  │ useHealth  │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │  HTTP + JSON (Axios → /api/v1)
                                     │  Proxied by Vite dev server (→ localhost:8000)
                                     │  Proxied by Nginx in production
┌────────────────────────────────────▼────────────────────────────────────────────┐
│                            FASTAPI BACKEND (Python 3.11)                         │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐     │
│  │                         Middleware Stack                                 │     │
│  │  CORSMiddleware → CorrelationIDMiddleware → TimingMiddleware → ExcHandler│     │
│  └──────────────────────────┬──────────────────────────────────────────────┘     │
│                             │                                                     │
│  ┌──────────────────────────▼──────────────────────────────────────────────┐     │
│  │                         FastAPI Router (/api/v1)                         │     │
│  │  POST /chat   GET /sessions   GET /monitoring   GET /health   POST /feed │     │
│  └──────────────────────────┬──────────────────────────────────────────────┘     │
│                             │                                                     │
│  ┌──────────────────────────▼──────────────────────────────────────────────┐     │
│  │                       Session Manager                                    │     │
│  │  • Generate/resolve Session ID                                           │     │
│  │  • Load conversation history from MongoDB                                │     │
│  │  • Build message context for LangGraph                                   │     │
│  └──────────────────────────┬──────────────────────────────────────────────┘     │
│                             │                                                     │
└─────────────────────────────┼───────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────────────────┐
│                         LANGGRAPH STATEGRAPH                                      │
│                                                                                   │
│    GraphState (TypedDict):                                                        │
│    message │ session_id │ correlation_id │ history │ intent │ confidence          │
│    response │ token_usage │ monitoring │ error                                    │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐     │
│  │                      ROUTER NODE                                         │     │
│  │  • Calls Groq LLaMA3 with intent classification prompt                  │     │
│  │  • Returns: { intent, confidence }                                       │     │
│  │  • Never answers the question                                            │     │
│  │  • Never contains business logic                                         │     │
│  └──────────────┬─────────────────────────────────────────────────────────┘     │
│                 │  conditional_edges                                               │
│     ┌───────────┼─────────────────────────────────┐                              │
│     │           │           │           │          │                              │
│  ┌──▼──┐  ┌─────▼──┐  ┌────▼───┐  ┌───▼──┐  ┌───▼────┐                         │
│  │ CON │  │  REIM  │  │ FOLLOW │  │ FAQ  │  │ ERROR  │                         │
│  │SULT │  │ BURSE  │  │   UP   │  │AGENT │  │HANDLER │                         │
│  │ATION│  │ MENT   │  │ AGENT  │  │      │  │        │                         │
│  └──┬──┘  └─────┬──┘  └────┬───┘  └───┬──┘  └───┬────┘                         │
│     └───────────┴──────────┴──────────┴──────────┘                              │
│                              │                                                    │
│  ┌───────────────────────────▼────────────────────────────────────────────┐     │
│  │                    MONITORING NODE                                       │     │
│  │  • Collects: latency, tokens, intent, agent, status                     │     │
│  │  • Writes MonitoringLog to MongoDB telemetry collection                 │     │
│  │  • No LLM call — pure Python                                            │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────────────────┐
│                         INFRASTRUCTURE LAYER                                      │
│                                                                                   │
│  ┌──────────────────────────┐    ┌─────────────────────────┐                     │
│  │         GROQ API         │    │        MONGODB 7.0       │                     │
│  │  llama3-8b-8192          │    │  Collections:            │                     │
│  │  Exponential backoff     │    │  • sessions              │                     │
│  │  Max 3 retries           │    │  • messages              │                     │
│  │  30s timeout             │    │  • telemetry             │                     │
│  │  LLMFactory DI pattern   │    │  • feedback              │                     │
│  └──────────────────────────┘    └─────────────────────────┘                     │
│                                                                                   │
│  ┌──────────────────────────┐                                                     │
│  │      LANGSMITH           │  (Optional)                                         │
│  │  Full trace visualization│                                                     │
│  │  LANGCHAIN_TRACING_V2    │                                                     │
│  └──────────────────────────┘                                                     │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## Request Lifecycle

```
1.  User types message in React ChatPage
2.  POST /api/v1/chat { message, session_id }
3.  CorrelationIDMiddleware assigns X-Correlation-ID
4.  TimingMiddleware starts clock
5.  SessionManager.load_or_create_session() → resolves/creates session
6.  SessionManager.get_history() → last N messages from MongoDB
7.  LangGraph graph.ainvoke(initial_state)
8.    → RouterNode classifies intent (Groq call #1)
9.    → conditional_edges selects agent node
10.   → SpecializedAgent generates response (Groq call #2)
11.   → MonitoringNode writes telemetry to MongoDB
12. ChatService saves user + assistant messages to MongoDB
13. ChatResponse returned to frontend
14. Frontend renders MessageBubble with structured data card
15. User optionally submits feedback (POST /api/v1/feedback)
```

---

## Data Flow Diagram

```
     ┌──────┐     POST /chat      ┌──────────┐   ainvoke()   ┌──────────────┐
     │ UI   │ ─────────────────▶  │ FastAPI  │ ────────────▶ │ LangGraph    │
     │      │ ◀──────────────── ─ │ Backend  │ ◀──────────── │ Graph        │
     └──────┘    ChatResponse      └─────┬────┘   GraphState  └──────┬───────┘
                                         │                           │
                                         │ save messages             │ read/write
                                         ▼                           ▼
                                    ┌──────────┐              ┌──────────────┐
                                    │ MongoDB  │              │  Groq API    │
                                    │          │              │  (LLM calls) │
                                    └──────────┘              └──────────────┘
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Router Pattern (not Supervisor)** | Simpler state, lower latency, intent classification only |
| **StateGraph with conditional_edges** | Graph-native routing, no if/else outside graph |
| **Router node never answers** | Single Responsibility Principle — classification only |
| **File-based prompt repository** | Prompts editable without code changes |
| **Pydantic structured outputs** | Type-safe, validated, serializable agent responses |
| **LLMFactory + dependency injection** | Easy provider swap, testable with MockGroqService |
| **Motor (async MongoDB)** | Non-blocking I/O compatible with FastAPI async |
| **mongomock_motor in tests** | Zero infrastructure required for CI |
| **Monitoring as graph node** | Telemetry always runs, decoupled from business logic |
