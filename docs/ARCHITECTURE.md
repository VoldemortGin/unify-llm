# Architecture Overview

## System Architecture

This document describes the architecture of UnifyLLM's MCP and A2A implementations.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         UnifyLLM Framework                       │
└─────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
            ┌───────▼───────┐ ┌──▼──────┐ ┌───▼────────┐
            │   LLM Layer   │ │   MCP   │ │    A2A     │
            │   Providers   │ │Protocol │ │  Protocol  │
            └───────┬───────┘ └──┬──────┘ └───┬────────┘
                    │             │             │
     ┌──────────────┼─────────────┼─────────────┼──────────────┐
     │              │             │             │              │
┌────▼────┐  ┌─────▼─────┐  ┌───▼────┐  ┌────▼─────┐  ┌─────▼─────┐
│ OpenAI  │  │ Anthropic │  │ Gemini │  │Databricks│  │  Ollama   │
└─────────┘  └───────────┘  └────────┘  └──────────┘  └───────────┘
```

---

## MCP (Model Context Protocol) Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Layer                               │
└─────────────────────────────────────────────────────────────┘

         ┌──────────────┐              ┌──────────────┐
         │  MCP Client  │◄────────────►│  MCP Server  │
         └──────┬───────┘              └──────┬───────┘
                │                              │
        ┌───────▼───────┐              ┌──────▼────────┐
        │  Transport    │              │   Registry    │
        │  - Stdio      │              │   - Tools     │
        │  - SSE        │              │   - Resources │
        │  - WebSocket  │              │   - Prompts   │
        └───────────────┘              └───────────────┘
                │                              │
        ┌───────▼────────────┐         ┌──────▼────────┐
        │ JSON-RPC Messages  │         │   Handlers    │
        │  - Request         │         │   - Execute   │
        │  - Response        │         │   - Validate  │
        │  - Notification    │         │   - Return    │
        └────────────────────┘         └───────────────┘
```

### MCP Message Flow

```
Client                Transport              Server
  │                      │                      │
  │─────Request─────────►│                      │
  │   (call tool)        │──────Forward────────►│
  │                      │                      │
  │                      │                      │──┐
  │                      │                      │  │ Execute
  │                      │                      │◄─┘ Tool
  │                      │                      │
  │                      │◄─────Response────────│
  │◄────Result───────────│                      │
  │                      │                      │
```

---

## A2A (Agent-to-Agent) Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      A2A Layer                               │
└─────────────────────────────────────────────────────────────┘

    ┌────────────────┐         ┌────────────────┐
    │  A2A Agent 1   │         │  A2A Agent 2   │
    │  - Base Agent  │         │  - Base Agent  │
    │  - Capabilities│         │  - Capabilities│
    │  - Handlers    │         │  - Handlers    │
    └────────┬───────┘         └───────┬────────┘
             │                         │
             └────────┬────────────────┘
                      │
         ┌────────────▼────────────┐
         │   Agent Registry        │
         │   - Discovery           │
         │   - Status Tracking     │
         │   - Heartbeat          │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │   Message Bus           │
         │   - Pub/Sub             │
         │   - Request/Response    │
         │   - Broadcast          │
         └─────────────────────────┘
```

### A2A Communication Flow

```
Agent A              Registry            Agent B
  │                     │                   │
  │──Register──────────►│                   │
  │                     │◄────Register──────│
  │                     │                   │
  │──Discover(skill)───►│                   │
  │◄──[Agent B]─────────│                   │
  │                     │                   │
  │──Delegate Task──────┼──────Forward─────►│
  │                     │                   │
  │                     │                   │──┐
  │                     │                   │  │ Execute
  │                     │                   │◄─┘ Task
  │                     │                   │
  │◄──────Result────────┼───────Return──────│
  │                     │                   │
```

---

## Collaboration Patterns

### 1. Sequential Collaboration

```
Task Input
    │
    ▼
┌────────────┐
│  Agent 1   │ Research
└─────┬──────┘
      │ Output
      ▼
┌────────────┐
│  Agent 2   │ Analyze
└─────┬──────┘
      │ Output
      ▼
┌────────────┐
│  Agent 3   │ Write
└─────┬──────┘
      │
      ▼
  Final Result
```

### 2. Parallel Collaboration

```
      Task Input
          │
    ┌─────┼─────┐
    ▼     ▼     ▼
┌───────┐ ┌───────┐ ┌───────┐
│Agent 1│ │Agent 2│ │Agent 3│
└───┬───┘ └───┬───┘ └───┬───┘
    │         │         │
    └─────────┼─────────┘
              ▼
        Aggregate Results
              │
              ▼
         Final Output
```

### 3. Consensus Collaboration

```
      Question
          │
    ┌─────┼─────┐
    ▼     ▼     ▼
┌───────┐ ┌───────┐ ┌───────┐
│Expert1│ │Expert2│ │Expert3│
│Vote: A│ │Vote: A│ │Vote: B│
└───┬───┘ └───┬───┘ └───┬───┘
    │         │         │
    └─────────┼─────────┘
              ▼
      Voting System
      (Majority/Unanimous)
              │
              ▼
      Decision: A
```

---

## Integration Architecture

### MCP + A2A Combined

```
┌──────────────────────────────────────────────────────┐
│                 Application Layer                     │
└──────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │                               │
┌───────▼────────┐              ┌──────▼──────┐
│   A2A Agents   │              │ MCP Clients │
│ (Communication)│◄────────────►│ (Tools)     │
└───────┬────────┘              └──────┬──────┘
        │                               │
        │         Message Bus           │
        └───────────────┬───────────────┘
                        │
                ┌───────▼────────┐
                │  MCP Servers   │
                │  (Tool Hosts)  │
                └────────────────┘
```

---

## Data Flow Example: Code Analysis

```
1. User Request
      │
      ▼
2. Coordinator Agent
      │
      ├──────────────┐
      │              │
      ▼              ▼
3. Code Analyzer  Security Auditor
   (A2A Agent)    (A2A Agent)
      │              │
      │  Uses MCP    │  Uses MCP
      ▼              ▼
4. File Server   Database Server
   (MCP Server)  (MCP Server)
      │              │
      ├──────┬───────┘
      │      │
      ▼      ▼
5. Analysis Results
      │
      ▼
6. Doc Writer Agent
   (A2A Agent)
      │
      ▼
7. Final Documentation
```

---

## Component Responsibilities

### MCP Components

| Component | Responsibility |
|-----------|----------------|
| **Client** | Connect to servers, call tools |
| **Server** | Expose tools, resources, prompts |
| **Transport** | Handle communication layer |
| **Protocol** | Define message structures |

### A2A Components

| Component | Responsibility |
|-----------|----------------|
| **Agent** | Wrap base agent with A2A |
| **Registry** | Track available agents |
| **Discovery** | Find agents by capability |
| **Collaboration** | Orchestrate multi-agent tasks |
| **Message Bus** | Coordinate communication |

---

## Technology Stack

```
┌─────────────────────────────────────┐
│      Python 3.8+                    │
└─────────────────────────────────────┘
         │
┌────────▼──────────────────────────┐
│  Core Libraries                    │
│  - asyncio (async/await)           │
│  - pydantic (data validation)      │
│  - aiohttp (HTTP/WebSocket)        │
└────────┬──────────────────────────┘
         │
┌────────▼──────────────────────────┐
│  UnifyLLM Core                     │
│  - LLM providers                   │
│  - Agent framework                 │
│  - Tool system                     │
└────────┬──────────────────────────┘
         │
┌────────▼──────────────────────────┐
│  Protocol Implementations          │
│  - MCP (this project)              │
│  - A2A (this project)              │
└────────────────────────────────────┘
```

---

## Deployment Scenarios

### 1. Single Process

```
┌─────────────────────────────┐
│      Python Process         │
│  ┌─────────────────────┐    │
│  │  Multiple Agents    │    │
│  │  + Message Bus      │    │
│  │  + MCP Servers      │    │
│  └─────────────────────┘    │
└─────────────────────────────┘
```

### 2. Multi-Process

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│Process 1 │  │Process 2 │  │Process 3 │
│  Agent A │  │  Agent B │  │  Agent C │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │
     └─────────────┼─────────────┘
                   │
           ┌───────▼────────┐
           │  Message Bus   │
           │  (Redis/Queue) │
           └────────────────┘
```

### 3. Distributed

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Server 1   │    │  Server 2   │    │  Server 3   │
│  Agent Team │    │  MCP Servers│    │  Database   │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                   │
       └──────────────────┼───────────────────┘
                          │
                  ┌───────▼────────┐
                  │   Network      │
                  │  Message Bus   │
                  └────────────────┘
```

---

## Security Considerations

```
┌─────────────────────────────────┐
│      Security Layers            │
├─────────────────────────────────┤
│  1. Authentication              │
│     - API keys                  │
│     - Agent credentials         │
├─────────────────────────────────┤
│  2. Authorization               │
│     - Capability-based access   │
│     - Tool permissions          │
├─────────────────────────────────┤
│  3. Communication               │
│     - TLS/SSL for network       │
│     - Message encryption        │
├─────────────────────────────────┤
│  4. Validation                  │
│     - Input validation          │
│     - Schema enforcement        │
└─────────────────────────────────┘
```

---

## Performance Optimization

### Async Architecture

```
Request 1 ──►┐
Request 2 ──►├──► Async Event Loop ──► Parallel Processing
Request 3 ──►┘         │
                       ├──► LLM Calls
                       ├──► Tool Execution
                       └──► Agent Communication
```

### Caching Strategy

```
Request
   │
   ▼
Cache Check ──Yes──► Return Cached
   │
   No
   │
   ▼
Execute ────────────► Update Cache
   │
   ▼
Return Result
```

---

**For implementation details, see the source code in `unify_llm/mcp/` and `unify_llm/a2a/`**
