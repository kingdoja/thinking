# QA Runtime Documentation

## Overview

The QA Runtime is a quality assurance system that executes automated checks on generated content during the workflow pipeline. It was implemented as part of Iteration 5 to enable the system to move from "能生成" (can generate) to "能返工、能审核、能放行" (can rework, can review, can approve).

## Components

### 1. QA Runtime Service (`app/services/qa_runtime.py`)

The core QA execution engine that:
- Executes different types of QA checks (rule, semantic, asset)
- Calculates quality scores and severity levels
- Generates QA reports
- Decides whether to block workflow continuation

**Key Methods:**
- `execute_qa()`: Main entry point for QA execution
- `should_block_workflow()`: Determines if QA results should block workflow
- `_calculate_qa_result()`: Calculates scores and severity from issues
- `_create_qa_report()`: Persists QA results to database

### 2. QA Stage Service (`app/services/qa_stage.py`)

Integrates QA checks into the workflow pipeline:
- Executes QA checks after media chain completion
- Updates StageTask with QA metrics
- Handles errors gracefully
- Provides workflow continuation decisions

**Key Methods:**
- `execute()`: Runs QA stage in workflow context
- `_update_stage_task()`: Records QA results in StageTask metrics

### 3. QA Repository (`app/repositories/qa_repository.py`)

Data access layer for QA reports:
- `list_for_episode()`: Get all QA reports for an episode
- `get_by_id()`: Get specific QA report
- `get_latest_for_stage()`: Get most recent QA report for a stage

## Data Models

### Issue

Represents a single QA issue:
```python
@dataclass
class Issue:
    type: str              # e.g., "missing_field", "invalid_format"
    severity: str          # "info", "minor", "major", "critical"
    location: str          # e.g., "brief.genre", "shot_3.dialogue"
    message: str           # Human-readable description
    suggestion: Optional[str]  # Suggested fix
```

### QAResult

Result of a QA check execution:
```python
@dataclass
class QAResult:
    result: str            # "passed", "failed", "warning"
    score: float           # Quality score 0-100
    severity: str          # Highest severity found
    issue_count: int
    issues: List[Issue]
    rerun_stage_type: Optional[str]  # Suggested stage to rerun
```

### QAReportModel (Database)

Persisted QA report in database:
- `qa_type`: Type of check (rule_check, semantic_check, asset_check)
- `target_ref_type`: What was checked (document, shot, asset, episode)
- `result`: Overall result (passed, failed, warning)
- `score`: Quality score (0-100)
- `severity`: Highest severity (info, minor, major, critical)
- `issues_jsonb`: List of issues found
- `rerun_stage_type`: Suggested stage to rerun if failed

## Scoring System

The QA Runtime uses a point-deduction scoring system:

- **Starting score**: 100.0
- **Critical issue**: -25 points each
- **Major issue**: -10 points each
- **Minor issue**: -3 points each
- **Info issue**: -1 point each
- **Minimum score**: 0.0 (never goes below zero)

## Workflow Blocking Logic

The QA Runtime blocks workflow continuation when:
1. Any issue has `severity == "critical"`
2. The overall `result == "failed"`

Workflows continue when:
- `result == "passed"` (no issues or only info/minor issues)
- `result == "warning"` (major issues but not critical)

## Integration with Media Workflow

The QA stage is integrated into the media workflow sequence:

```python
MEDIA_STAGE_SEQUENCE = [
    "image_render",
    "subtitle",
    "tts",
    "edit_export_preview",
    "qa",  # QA check after media chain
]
```

After the preview export completes, the QA stage:
1. Executes rule checks on the episode
2. Executes semantic checks on the episode
3. Records results in QAReport table
4. Updates StageTask with metrics
5. Decides whether to block further workflow stages

## Usage Example

```python
from app.services.qa_runtime import QARuntime

# Initialize QA Runtime
qa_runtime = QARuntime(db_session)

# Execute QA check
qa_result = qa_runtime.execute_qa(
    episode_id=episode_id,
    stage_task_id=stage_task_id,
    qa_type="rule_check",
    target_ref_type="episode",
    target_ref_id=None,
)

# Check if workflow should be blocked
should_block = qa_runtime.should_block_workflow(qa_result)

if should_block:
    # Handle blocking (e.g., pause workflow, notify user)
    print(f"QA failed with {qa_result.issue_count} issues")
else:
    # Continue workflow
    print(f"QA passed with score {qa_result.score}")
```

## Future Enhancements

The current implementation provides the framework for QA checks. Future tasks will implement:

1. **Rule Checks** (Task 2): Validate required fields, formats, and structure
2. **Semantic Checks** (Task 3): Verify character consistency, world-building, plot coherence
3. **Asset Quality Checks**: Validate media file integrity and technical specs
4. **Custom Rules Engine**: Allow users to define custom QA rules

## Testing

Unit tests are provided in:
- `tests/unit/test_qa_runtime.py`: Tests for QA Runtime core logic
- `tests/unit/test_qa_stage.py`: Tests for QA Stage integration

Run tests with:
```bash
python -m pytest tests/unit/test_qa_runtime.py -v
```

## Requirements Implemented

This implementation satisfies the following requirements from the design document:

- **Requirement 1.1**: QA Runtime executes checks and creates QAReport records
- **Requirement 1.2**: QA reports include issues_jsonb, score, and severity
- **Requirement 1.3**: QA results determine workflow continuation
- **Requirement 1.4**: QA stage executes after media chain completion
- **Requirement 1.5**: QA results decide whether to block workflow

## Related Documentation

- Design Document: `.kiro/specs/qa-review-rerun/design.md`
- Requirements: `.kiro/specs/qa-review-rerun/requirements.md`
- Tasks: `.kiro/specs/qa-review-rerun/tasks.md`
