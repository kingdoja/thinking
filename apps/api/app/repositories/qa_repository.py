from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import QAReportModel


class QARepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_episode(self, episode_id: UUID) -> List[QAReportModel]:
        stmt = (
            select(QAReportModel)
            .where(QAReportModel.episode_id == episode_id)
            .order_by(QAReportModel.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())
    
    def get_by_id(self, report_id: UUID) -> Optional[QAReportModel]:
        """Get QA report by ID."""
        return self.db.get(QAReportModel, report_id)
    
    def get_latest_for_stage(
        self,
        episode_id: UUID,
        stage_task_id: UUID,
    ) -> Optional[QAReportModel]:
        """Get the latest QA report for a specific stage task."""
        stmt = (
            select(QAReportModel)
            .where(
                QAReportModel.episode_id == episode_id,
                QAReportModel.stage_task_id == stage_task_id,
            )
            .order_by(QAReportModel.created_at.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()
