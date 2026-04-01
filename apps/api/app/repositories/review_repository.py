from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ReviewDecisionModel


class ReviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, commit: bool = True, **kwargs) -> ReviewDecisionModel:
        review = ReviewDecisionModel(**kwargs)
        self.db.add(review)
        if commit:
            self.db.commit()
            self.db.refresh(review)
        else:
            self.db.flush()
        return review

    def list_for_episode(self, episode_id) -> list[ReviewDecisionModel]:
        stmt = (
            select(ReviewDecisionModel)
            .where(ReviewDecisionModel.episode_id == episode_id)
            .order_by(ReviewDecisionModel.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def latest_for_episode(self, episode_id):
        stmt = (
            select(ReviewDecisionModel)
            .where(ReviewDecisionModel.episode_id == episode_id)
            .order_by(ReviewDecisionModel.created_at.desc())
        )
        return self.db.scalars(stmt).first()

    def latest_for_stage_task(self, stage_task_id):
        stmt = (
            select(ReviewDecisionModel)
            .where(ReviewDecisionModel.stage_task_id == stage_task_id)
            .order_by(ReviewDecisionModel.created_at.desc())
        )
        return self.db.scalars(stmt).first()
