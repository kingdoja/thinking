"""
QA Stage Service

Executes QA checks as part of the workflow pipeline.
Implements Requirements: 1.4, 1.5

The QA Stage is responsible for:
1. Executing QA checks after media chain completion
2. Deciding whether to allow workflow continuation
3. Recording QA results in StageTask metrics
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.stage_task_repository import StageTaskRepository
from app.services.qa_runtime import QARuntime, QAResult


@dataclass
class QAStageResult:
    """Result of QA stage execution."""
    status: str  # "passed", "failed", "warning"
    qa_results: List[QAResult] = field(default_factory=list)
    should_block: bool = False
    execution_time_ms: int = 0
    errors: List[str] = field(default_factory=list)


class QAStage:
    """
    QA Stage - executes quality assurance checks in the workflow.
    
    Responsibilities:
    1. Execute QA checks after media chain (Requirement 1.4)
    2. Decide workflow continuation (Requirement 1.5)
    3. Update StageTask with QA results
    
    Implements Requirements: 1.4, 1.5
    """
    
    def __init__(self, db: Session):
        """
        Initialize QA Stage.
        
        Args:
            db: Database session
        """
        self.db = db
        self.qa_runtime = QARuntime(db)
        self.stage_task_repo = StageTaskRepository(db)
    
    def execute(
        self,
        episode_id: UUID,
        project_id: UUID,
        stage_task_id: UUID,
    ) -> QAStageResult:
        """
        Execute QA stage checks.
        
        Implements Requirements: 1.4, 1.5
        
        Args:
            episode_id: Episode ID
            project_id: Project ID
            stage_task_id: StageTask ID for this QA stage
            
        Returns:
            QAStageResult with check results
        """
        import time
        start_time = time.time()
        
        qa_results: List[QAResult] = []
        errors: List[str] = []
        should_block = False
        
        try:
            # Update stage task to running
            self.stage_task_repo.update_status(
                stage_task_id,
                "running",
                started_at=datetime.utcnow(),
                commit=True,
            )
            
            # Execute episode-level rule check (Requirement 1.4)
            try:
                rule_check_result = self.qa_runtime.execute_qa(
                    episode_id=episode_id,
                    stage_task_id=stage_task_id,
                    qa_type="rule_check",
                    target_ref_type="episode",
                    target_ref_id=None,
                )
                qa_results.append(rule_check_result)
                
                # Check if this result should block workflow (Requirement 1.5)
                if self.qa_runtime.should_block_workflow(rule_check_result):
                    should_block = True
                    
            except Exception as e:
                error_msg = f"Rule check failed: {str(e)}"
                errors.append(error_msg)
            
            # Execute episode-level semantic check (Requirement 1.4)
            try:
                semantic_check_result = self.qa_runtime.execute_qa(
                    episode_id=episode_id,
                    stage_task_id=stage_task_id,
                    qa_type="semantic_check",
                    target_ref_type="episode",
                    target_ref_id=None,
                )
                qa_results.append(semantic_check_result)
                
                # Check if this result should block workflow (Requirement 1.5)
                if self.qa_runtime.should_block_workflow(semantic_check_result):
                    should_block = True
                    
            except Exception as e:
                error_msg = f"Semantic check failed: {str(e)}"
                errors.append(error_msg)
            
            # Determine overall status
            if should_block:
                status = "failed"
            elif errors:
                status = "warning"
            else:
                # Check if any QA result is failed
                has_failures = any(r.result == "failed" for r in qa_results)
                if has_failures:
                    status = "failed"
                    should_block = True
                else:
                    status = "passed"
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Update stage task with results
            self._update_stage_task(
                stage_task_id=stage_task_id,
                status=status,
                qa_results=qa_results,
                execution_time_ms=execution_time_ms,
                errors=errors,
            )
            
            return QAStageResult(
                status=status,
                qa_results=qa_results,
                should_block=should_block,
                execution_time_ms=execution_time_ms,
                errors=errors,
            )
            
        except Exception as e:
            # Handle unexpected errors
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"QA stage failed with exception: {str(e)}"
            errors.append(error_msg)
            
            # Update stage task as failed
            self.stage_task_repo.update_status(
                stage_task_id,
                "failed",
                finished_at=datetime.utcnow(),
                error_message=error_msg,
                commit=True,
            )
            
            return QAStageResult(
                status="failed",
                qa_results=qa_results,
                should_block=True,
                execution_time_ms=execution_time_ms,
                errors=errors,
            )
    
    def _update_stage_task(
        self,
        stage_task_id: UUID,
        status: str,
        qa_results: List[QAResult],
        execution_time_ms: int,
        errors: List[str],
    ) -> None:
        """
        Update StageTask with QA execution results.
        
        Args:
            stage_task_id: StageTask ID
            status: Final status
            qa_results: List of QA results
            execution_time_ms: Execution time
            errors: List of errors
        """
        # Build metrics
        metrics = {
            'execution_time_ms': execution_time_ms,
            'checks_executed': len(qa_results),
            'checks_passed': sum(1 for r in qa_results if r.result == "passed"),
            'checks_failed': sum(1 for r in qa_results if r.result == "failed"),
            'total_issues': sum(r.issue_count for r in qa_results),
            'critical_issues': sum(
                sum(1 for issue in r.issues if issue.severity == "critical")
                for r in qa_results
            ),
            'major_issues': sum(
                sum(1 for issue in r.issues if issue.severity == "major")
                for r in qa_results
            ),
        }
        
        # Update metrics
        self.stage_task_repo.update_metrics(
            stage_task_id,
            metrics=metrics,
            commit=False,
        )
        
        # Determine final task status
        task_status = "succeeded" if status in ["passed", "warning"] else "failed"
        
        # Update status
        error_message = None
        if errors:
            error_message = "; ".join(errors[:3])
        
        self.stage_task_repo.update_status(
            stage_task_id,
            task_status,
            finished_at=datetime.utcnow(),
            error_message=error_message,
            commit=True,
        )
