# AI Comic Drama Production Platform

[简体中文](./README.md) | English

> AI-powered production platform for transforming web novels into vertical-format comic dramas, designed for short-video platforms.

## Project Overview

Full-stack AI production platform that orchestrates multiple specialized AI agents to automate the creative pipeline from source material to storyboard. Demonstrates advanced workflow orchestration, agent architecture, and production-grade software engineering practices.

**Use Case**: Converting Chinese web novels into structured storyboards for vertical short-form video production.

## Architecture Highlights

### Design Principles

1. **Workflow-First**: Business logic driven by explicit workflow orchestration
2. **Artifact-First**: System state derived from structured artifacts, not chat context
3. **Runtime Separation**: Clear separation between agents, orchestration, and persistence
4. **Explicit State**: All states explicitly modeled, traceable, and rollback-capable
5. **Anti-Drift**: Multi-layer consistency checks prevent content deviation

### Tech Stack

**Backend**: Python 3.8+ • FastAPI • PostgreSQL 16 • SQLAlchemy 2.0 • Redis

**Frontend**: Next.js 14 • TypeScript • React 18 • TailwindCSS • Radix UI

**Infrastructure**: Docker • MinIO • Alembic

**Testing**: pytest • Hypothesis (PBT) • 89% coverage

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          API Layer                              │
│  POST /workflow/start  │  GET /workspace  │  PUT /documents    │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────────────────────────┐
│                   Workflow Orchestrator                         │
│  • Episode workflow state machine                               │
│  • Stage task input builder                                     │
│  • Retry & failure handler                                      │
│  • Execution logging & metrics                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Runtime                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Brief Agent  │  │ Story Bible  │  │  Character   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐                           │
│  │ Script Agent │  │  Storyboard  │                           │
│  └──────────────┘  └──────────────┘                           │
│                                                                 │
│  Pipeline: Loader → Normalizer → Planner → Generator →         │
│            Critic → Validator → Committer                      │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                 │
│  PostgreSQL: projects, episodes, workflows, documents, shots    │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Pipeline

Each agent follows a standardized 7-stage pipeline:

```python
class BaseAgent:
    def execute(self, task_input: StageTaskInput) -> StageTaskOutput:
        context = self.loader.load(task_input.input_refs)
        normalized = self.normalizer.normalize(context)
        plan = self.planner.build(normalized)
        draft = self.generator.generate(plan)
        reviewed = self.critic.review(draft, normalized)
        valid = self.validator.validate(reviewed)
        refs = self.committer.commit(valid)
        return StageTaskOutput(...)
```

### Agent Specializations

1. **Brief Agent**: Extracts creative direction from source material
2. **Story Bible Agent**: Establishes world rules and constraints
3. **Character Agent**: Defines character profiles with visual anchors
4. **Script Agent**: Generates scene-by-scene script with dialogue
5. **Storyboard Agent**: Creates shot-level specifications

## Workflow Orchestration

- **Builds Stage Inputs**: Constructs inputs with proper document references
- **Handles Agent Outputs**: Processes outputs and decides next actions
- **Manages Failures**: Retry logic (max 3 attempts) with exponential backoff
- **Preserves Artifacts**: All intermediate artifacts preserved on failure
- **Tracks Execution**: Logs stage start/completion, duration, token usage

### Failure Isolation

- Brief failure → No impact on project
- Story Bible failure → Brief remains intact
- Character failure → Brief and Story Bible intact
- Script failure → Previous version protected
- Storyboard failure → Script and upstream documents intact

## Data Models

**WorkflowRun**: Tracks end-to-end workflow execution  
**StageTask**: Represents individual agent execution  
**Document**: Versioned structured content with lockable fields  
**Shot**: Atomic visual unit for storyboard

## Testing Strategy

### Unit Testing (39 passing tests)

- Service Layer: Workflow orchestration, document validation
- Repository Layer: CRUD operations, version management
- Agent Pipeline: Stage isolation, error propagation

### Property-Based Testing

Using Hypothesis with 100+ iterations per property:

```python
@given(st.text(min_size=1), st.integers(min_value=1))
def test_document_version_increment(content, current_version):
    """For any document edit, version should increment by exactly 1"""
    new_doc = edit_document(content, current_version)
    assert new_doc.version == current_version + 1
```

## Key Technical Decisions

### 1. Workflow-First vs Agent-First

**Decision**: Workflow orchestrator controls execution flow

**Rationale**: Centralized retry logic, human review gates, traceable execution, partial rerun support

### 2. Artifact-First State Management

**Decision**: System state derived from structured documents

**Rationale**: Versioned and auditable, state reconstruction, rollback support, parallel execution

### 3. Consistency Critic Pattern

**Decision**: Each agent includes self-review "Critic" stage

**Rationale**: Early drift detection, actionable warnings, non-blocking execution, quality signals

### 4. Locked Field Protection

**Decision**: Critical fields can be locked

**Rationale**: Prevents downstream changes, iterative refinement, preserves human edits, creative anchors

## Project Structure

```
.
├── apps/
│   ├── api/                    # FastAPI backend
│   └── web/                    # Next.js frontend
├── workers/
│   ├── agent-runtime/          # AI agent implementations
│   ├── media-runtime/          # Image/video generation
│   └── qa-runtime/             # Quality assurance
├── infra/
│   ├── docker/                 # Docker Compose setup
│   ├── migrations/             # Alembic migrations
│   └── temporal/               # Temporal workflows
└── docs/
    ├── product/                # Product specs & PRDs
    ├── design/                 # Design system
    └── engineering/            # Technical docs
```

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- Docker & Docker Compose

### Setup

1. **Start infrastructure**:
```bash
cd infra/docker
docker-compose up -d postgres redis minio
```

2. **Setup Python virtual environment**:
```bash
cd apps/api

# Create virtual environment (project uses .venv)
python -m venv .venv

# Activate virtual environment
# Linux/Mac:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

3. **Run migrations**:
```bash
cd infra/migrations
alembic upgrade head
```

4. **Run tests**:
```bash
cd apps/api
pytest tests/ -v
```

5. **Start API**:
```bash
uvicorn app.main:app --reload --port 8000
```

6. **Start frontend**:
```bash
cd apps/web
npm install && npm run dev
```

Access: `http://localhost:3000`

## Current Status

**Completed**:
- ✅ Core data models and repositories
- ✅ Workflow orchestration service
- ✅ All 5 text agents with 7-stage pipeline
- ✅ Document validation and locked field protection
- ✅ Consistency checking (Critic component)
- ✅ Error handling and retry logic
- ✅ Unit test suite (39 tests, 89% coverage)
- ✅ Property-based testing framework

**In Progress**:
- 🔄 Integration tests
- 🔄 Frontend workspace UI
- 🔄 Temporal workflow integration

**Planned**:
- 📋 Media generation agents
- 📋 QA agent
- 📋 Human review UI

## Technical Highlights

1. **Distributed Systems**: Workflow orchestration, state management, failure handling
2. **AI Engineering**: Multi-agent coordination, prompt engineering, consistency checking
3. **Software Architecture**: Clean architecture, repository pattern, dependency injection
4. **Testing**: Unit testing, property-based testing, test-driven development
5. **Database Design**: Versioning, soft deletes, audit trails, indexing strategies
6. **API Design**: RESTful APIs, request/response schemas, error handling
7. **DevOps**: Docker containerization, database migrations, environment management

## Documentation

- **Product Specs**: `docs/product/` - Product vision, MVP plan, PRDs
- **Technical Docs**: `docs/engineering/` - API contracts, agent architecture
- **Design System**: `docs/design/` - UI components, design tokens
- **Feature Specs**: `.kiro/specs/` - Detailed requirements and design

## License

This project is for technical demonstration and learning purposes only.

---

**Last Updated**: April 2026
