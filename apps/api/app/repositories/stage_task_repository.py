from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import StageTaskModel


class StageTaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, task_id):
        return self.db.get(StageTaskModel, task_id)

    def create(self, commit: bool = True, **kwargs) -> StageTaskModel:
        stage_task = StageTaskModel(**kwargs)
        self.db.add(stage_task)
        if commit:
            self.db.commit()
            self.db.refresh(stage_task)
        else:
            self.db.flush()
        return stage_task

    def list_for_workflow(self, workflow_run_id) -> List[StageTaskModel]:
        stmt = (
            select(StageTaskModel)
            .where(StageTaskModel.workflow_run_id == workflow_run_id)
            .order_by(StageTaskModel.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_for_episode(self, episode_id) -> List[StageTaskModel]:
        stmt = (
            select(StageTaskModel)
            .where(StageTaskModel.episode_id == episode_id)
            .order_by(StageTaskModel.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def latest_by_stage(self, episode_id, stage_type):
        stmt = (
            select(StageTaskModel)
            .where(
                StageTaskModel.episode_id == episode_id,
                StageTaskModel.stage_type == stage_type,
            )
            .order_by(StageTaskModel.created_at.desc())
        )
        return self.db.scalars(stmt).first()

    def update_status(self, task_id, task_status: str, **updates):
        stage_task = self.get(task_id)
        if stage_task is None:
            return None

        stage_task.task_status = task_status
        for key, value in updates.items():
            setattr(stage_task, key, value)

        self.db.add(stage_task)
        self.db.commit()
        self.db.refresh(stage_task)
        return stage_task

    def update_review_status(self, task_id, review_status: str, commit: bool = True):
        stage_task = self.get(task_id)
        if stage_task is None:
            return None

        stage_task.review_status = review_status
        self.db.add(stage_task)
        if commit:
            self.db.commit()
            self.db.refresh(stage_task)
        else:
            self.db.flush()
        return stage_task

    def update_metrics(self, task_id, metrics: dict, commit: bool = True):
        """
        Update the metrics_jsonb field for a stage task.
        
        Implements Requirement 10.5: Record execution metrics
        
        Args:
            task_id: StageTask ID
            metrics: Dictionary containing execution metrics
            commit: Whether to commit the transaction
            
        Returns:
            Updated StageTask model or None if not found
        """
        stage_task = self.get(task_id)
        if stage_task is None:
            return None

        stage_task.metrics_jsonb = metrics
        self.db.add(stage_task)
        if commit:
            self.db.commit()
            self.db.refresh(stage_task)
        else:
            self.db.flush()
        return stage_task
