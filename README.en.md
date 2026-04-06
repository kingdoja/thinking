# AI Comic Drama Production Platform

> An AI-powered production platform for transforming web novels into vertical-format comic dramas, designed for short-video platforms like Douyin and Kuaishou.

## ?? Project Overview

This is a full-stack AI production platform that orchestrates multiple specialized AI agents to automate the creative pipeline from source material to storyboard. The system demonstrates advanced workflow orchestration, agent architecture, and production-grade software engineering practices.

**Target Use Case**: Converting Chinese web novels (particularly female-oriented romance/revenge stories) into structured storyboards for vertical short-form video production.

## ??? Architecture Highlights

### System Design Principles

1. **Workflow-First Architecture**: Business logic is driven by explicit workflow orchestration, not implicit agent chaining
2. **Artifact-First State Management**: System state is derived from structured artifacts (documents, shots), not chat context
3. **Runtime Separation**: Clear separation between text generation (agents), orchestration (workflow), and persistence (repositories)
4. **Explicit State Modeling**: All states are explicitly modeled, traceable, and rollback-capable
5. **Anti-Drift Mechanisms**: Multi-layer consistency checks prevent content from deviating from original creative direction

### Technology Stack

**Backend**:
- Python 3.8+ with FastAPI
- PostgreSQL 16 (primary data store)
- SQLAlchemy 2.0 (ORM with async support)
- Temporal (workflow orchestration - planned)
- Redis (caching and session management)

**Frontend**:
- Next.js 14 with TypeScript
- React 18 with Server Components
- TailwindCSS for styling
- Radix UI for accessible components

**Infrastructure**:
- Docker & Docker Compose
- MinIO (S3-compatible object storage)
- Alembic (database migrations)

**Testing**:
- pytest with pytest-asyncio
- Hypothesis (property-based testing)
- 89% test coverage on core services

## ?? System Architecture

```
©°©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©´
©¦                          API Layer                              ©¦
©¦  POST /workflow/start  ©¦  GET /workspace  ©¦  PUT /documents    ©¦
©¸©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©Ð©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¼
                 ©¦
                 v
©°©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©´
©¦                   Workflow Orchestrator                         ©¦
©¦  ? Episode workflow state machine                               ©¦
©¦  ? Stage task input builder                                     ©¦
©¦  ? Retry & failure handler                                      ©¦
©¦  ? Execution logging & metrics                                  ©¦
©¸©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©Ð©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¼
                 ©¦
                 v
©°©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©´
©¦                      Agent Runtime                              ©¦
©¦  ©°©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©´  ©°©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©´  ©°©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©´         ©¦
©¦  ©¦ Brief Agent  ©¦  ©¦ Story Bible  ©¦  ©¦  Character   ©¦         ©¦
©¦  ©¦              ©¦  ©¦    Agent     ©¦  ©¦    Agent     ©¦         ©¦
©¦  ©¸©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¼  ©¸©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¼  ©¸©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¼         ©¦
©¦  ©°©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©´  ©°©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©´                           ©¦
©¦  ©¦ Script Agent ©¦  ©¦  Storyboard  ©¦                           ©¦
©¦  ©¦              ©¦  ©¦    Agent     ©¦                           ©¦
©¦  ©¸©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¼  ©¸©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¼                           ©¦
©¦                                                                 ©¦
©¦  Common Pipeline: Loader ¡ú Normalizer ¡ú Planner ¡ú              ©¦
©¦                   Generator ¡ú Critic ¡ú Validator ¡ú Committer   ©¦
©¸©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©Ð©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¼
                 ©¦
                 v
©°©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©´
©¦                      Data Layer                                 ©¦
©¦  PostgreSQL: projects, episodes, workflow_runs, stage_tasks,    ©¦
©¦              documents, shots                                   ©¦
©¦  Repositories: ProjectRepo, EpisodeRepo, WorkflowRepo,          ©¦
©¦                DocumentRepo, ShotRepo, StageTaskRepo            ©¦
©¸©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¼
```

## ?? Agent Pipeline Architecture

Each agent follows a standardized 7-stage pipeline:

```python
class BaseAgent:
    def execute(self, task_input: StageTaskInput) -> StageTaskOutput:
        # 1. Loader: Load input documents and references
        context = self.loader.load(task_input.input_refs, task_input.locked_refs)
        
        # 2. Normalizer: Clean and structure context
        normalized = self.normalizer.normalize(context, task_input.constraints)
        
        # 3. Planner: Create execution plan
        plan = self.planner.build(normalized, task_input.stage_type)
        
        # 4. Generator: Call LLM to generate content
        draft = self.generator.generate(plan, schema=self.output_schema)
        
        # 5. Critic: Self-review for consistency
        reviewed = self.critic.review(draft, normalized)
        
        # 6. Validator: Validate schema and constraints
        valid = self.validator.validate(reviewed, task_input.locked_refs)
        
        # 7. Committer: Persist to database
        refs = self.committer.commit(valid, task_input.project_id, task_input.episode_id)
        
        return StageTaskOutput(...)
```

### Agent Specializations

1. **Brief Agent**: Extracts core creative direction from source material
   - Input: Raw novel excerpt, platform constraints, target audience
   - Output: Genre, selling points, main conflict, adaptation strategy

2. **Story Bible Agent**: Establishes world rules and constraints
   - Input: Brief, material summary
   - Output: World rules, timeline, forbidden conflicts, key settings

3. **Character Agent**: Defines character profiles with visual anchors
   - Input: Brief, Story Bible
   - Output: Character profiles with personality, goals, visual descriptions

4. **Script Agent**: Generates scene-by-scene script with dialogue
   - Input: Brief, Story Bible, Character profiles
   - Output: Structured scenes with dialogue, emotion beats, timing

5. **Storyboard Agent**: Creates shot-level specifications
   - Input: Script, platform constraints
   - Output: Shot records with camera angles, composition, visual prompts

## ?? Workflow Orchestration

The workflow service implements a state machine that:

- **Builds Stage Inputs**: Constructs `StageTaskInput` with proper document references and constraints
- **Handles Agent Outputs**: Processes `StageTaskOutput` and decides next actions
- **Manages Failures**: Implements retry logic (max 3 attempts) with exponential backoff
- **Preserves Artifacts**: On failure, all intermediate artifacts are preserved for recovery
- **Tracks Execution**: Logs stage start/completion, duration, token usage, and errors

### Failure Isolation

Each stage failure is isolated:
- Brief failure ¡ú No impact on project
- Story Bible failure ¡ú Brief remains intact
- Character failure ¡ú Brief and Story Bible remain intact
- Script failure ¡ú Previous version protected, upstream documents intact
- Storyboard failure ¡ú Script and all upstream documents intact

## ?? Data Models

### Core Entities

**WorkflowRun**: Tracks end-to-end workflow execution
- Status: created ¡ú running ¡ú succeeded/failed
- Links to Temporal workflow (for distributed execution)
- Supports rerun from specific stage

**StageTask**: Represents individual agent execution
- Tracks input/output references
- Records retry attempts and errors
- Supports review gates for human approval

**Document**: Versioned structured content
- Type-specific JSON schemas (brief, story_bible, character_profile, etc.)
- Version history with creator tracking (AI vs human)
- Lockable fields to prevent downstream drift

**Shot**: Atomic visual unit for storyboard
- Camera specifications (size, angle, movement)
- Character references and visual constraints
- Duration and sequencing information

## ?? Testing Strategy

### Unit Testing (39 passing tests)

- **Service Layer**: Workflow orchestration, document validation, review logic
- **Repository Layer**: CRUD operations, version management, query methods
- **Agent Pipeline**: Individual pipeline stage isolation, error propagation

### Property-Based Testing (Framework ready)

Using Hypothesis for PBT with 100+ iterations per property:

- **Workflow Properties**: Stage order preservation, artifact isolation on failure
- **Document Properties**: Required field validation, version increment correctness
- **Consistency Properties**: Brief alignment, character behavior consistency, world rule compliance
- **Workspace Properties**: Complete aggregation, latest version selection

Example property test:
```python
@given(st.text(min_size=1), st.integers(min_value=1))
def test_document_version_increment(content, current_version):
    """For any document edit, version should increment by exactly 1"""
    new_doc = edit_document(content, current_version)
    assert new_doc.version == current_version + 1
```

## ?? Key Technical Decisions

### 1. Workflow-First vs Agent-First

**Decision**: Workflow orchestrator controls execution flow, agents are stateless workers.

**Rationale**: 
- Enables centralized retry logic and failure handling
- Allows workflow to be paused for human review
- Makes execution traceable and debuggable
- Supports partial rerun from any stage

### 2. Artifact-First State Management

**Decision**: System state is derived from structured documents, not chat history.

**Rationale**:
- Documents are versioned and auditable
- State can be reconstructed from artifacts
- Supports rollback and branching
- Enables parallel execution of independent stages

### 3. Consistency Critic Pattern

**Decision**: Each agent includes a self-review "Critic" stage that checks consistency.

**Rationale**:
- Catches drift early before persistence
- Generates actionable warnings for human review
- Doesn't block execution (warnings, not errors)
- Provides quality signals for downstream stages

### 4. Locked Field Protection

**Decision**: Critical fields (character names, visual anchors, core conflicts) can be locked.

**Rationale**:
- Prevents downstream agents from changing established facts
- Enables iterative refinement without breaking consistency
- Supports human edits that must be preserved
- Implements "creative anchors" pattern

## ?? Project Structure

```
.
©À©¤©¤ apps/
©¦   ©À©¤©¤ api/                    # FastAPI backend
©¦   ©¦   ©À©¤©¤ app/
©¦   ©¦   ©¦   ©À©¤©¤ api/           # API routes
©¦   ©¦   ©¦   ©À©¤©¤ db/            # Database models
©¦   ©¦   ©¦   ©À©¤©¤ repositories/  # Data access layer
©¦   ©¦   ©¦   ©À©¤©¤ schemas/       # Pydantic schemas
©¦   ©¦   ©¦   ©¸©¤©¤ services/      # Business logic
©¦   ©¦   ©¸©¤©¤ tests/             # Unit & integration tests
©¦   ©¸©¤©¤ web/                   # Next.js frontend
©À©¤©¤ workers/
©¦   ©À©¤©¤ agent-runtime/         # AI agent implementations
©¦   ©¦   ©À©¤©¤ base_agent.py     # Common pipeline
©¦   ©¦   ©À©¤©¤ brief_agent.py    # Brief generation
©¦   ©¦   ©À©¤©¤ story_bible_agent.py
©¦   ©¦   ©À©¤©¤ character_agent.py
©¦   ©¦   ©À©¤©¤ script_agent.py
©¦   ©¦   ©¸©¤©¤ storyboard_agent.py
©¦   ©À©¤©¤ media-runtime/         # Image/video generation
©¦   ©¸©¤©¤ qa-runtime/            # Quality assurance
©À©¤©¤ infra/
©¦   ©À©¤©¤ docker/                # Docker Compose setup
©¦   ©À©¤©¤ migrations/            # Alembic migrations
©¦   ©¸©¤©¤ temporal/              # Temporal workflows
©À©¤©¤ docs/
©¦   ©À©¤©¤ product/               # Product specs & PRDs
©¦   ©À©¤©¤ design/                # Design system
©¦   ©À©¤©¤ engineering/           # Technical docs
©¦   ©¸©¤©¤ interview/             # Interview prep materials
©¸©¤©¤ .kiro/specs/               # Feature specifications
```

## ?? Getting Started

### Prerequisites

- Python 3.8+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 16 (via Docker)

### Quick Start

1. **Start infrastructure**:
```bash
cd infra/docker
docker-compose up -d postgres redis minio
```

2. **Set up Python environment**:
```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. **Run database migrations**:
```bash
cd infra/migrations
alembic upgrade head
```

4. **Run tests**:
```bash
cd apps/api
pytest tests/ -v
```

5. **Start API server**:
```bash
cd apps/api
uvicorn app.main:app --reload --port 8000
```

6. **Start frontend** (in separate terminal):
```bash
cd apps/web
npm install
npm run dev
```

Access the application at `http://localhost:3000`

## ?? Current Status

**Completed**:
- ? Core data models and repositories
- ? Workflow orchestration service
- ? All 5 text agents (Brief, Story Bible, Character, Script, Storyboard)
- ? Agent pipeline framework with 7-stage execution
- ? Document validation and locked field protection
- ? Workspace aggregation API
- ? Consistency checking (Critic component)
- ? Error handling and retry logic
- ? Execution logging and metrics
- ? Unit test suite (39 tests passing)
- ? Property-based testing framework setup

**In Progress**:
- ?? Integration tests with real database
- ?? Frontend workspace UI
- ?? Temporal workflow integration

**Planned**:
- ?? Media generation agents (image, video)
- ?? QA agent for quality assurance
- ?? Human review UI
- ?? Asset management system

## ?? Learning Highlights

This project demonstrates:

1. **Distributed Systems**: Workflow orchestration, state management, failure handling
2. **AI Engineering**: Multi-agent coordination, prompt engineering, consistency checking
3. **Software Architecture**: Clean architecture, repository pattern, dependency injection
4. **Testing**: Unit testing, property-based testing, test-driven development
5. **Database Design**: Versioning, soft deletes, audit trails, indexing strategies
6. **API Design**: RESTful APIs, request/response schemas, error handling
7. **DevOps**: Docker containerization, database migrations, environment management

## ?? Documentation

- **Product Specs**: `docs/product/` - Product vision, MVP plan, PRDs
- **Technical Docs**: `docs/engineering/` - API contracts, agent architecture, workflow design
- **Design System**: `docs/design/` - UI components, design tokens, style guide

## ?? License

This is a portfolio/interview project. Not licensed for commercial use.

---

**Author**: [Your Name]  
**Contact**: [Your Email]  
**Last Updated**: April 2026



