from sqlalchemy.orm import Session

from app.repositories.review_repository import ReviewRepository
from app.repositories.stage_task_repository import StageTaskRepository
from app.schemas.workspace import SubmitReviewDecisionRequest


class ReviewService:
    def __init__(
        self,
        db: Session,
        stage_tasks: StageTaskRepository,
        reviews: ReviewRepository,
    ) -> None:
        self.db = db
        self.stage_tasks = stage_tasks
        self.reviews = reviews

    def submit_review_decision(self, project_id, episode_id, payload: SubmitReviewDecisionRequest):
        stage_task = self.stage_tasks.get(payload.stage_task_id)
        if stage_task is None:
            raise LookupError("Stage task not found")

        if str(stage_task.project_id) != str(project_id) or str(stage_task.episode_id) != str(episode_id):
            raise LookupError("Stage task not found")

        if not stage_task.review_required:
            raise ValueError("Stage task does not require review")

        if stage_task.task_status != "succeeded":
            raise ValueError("Stage task must be succeeded before review")

        review = self.reviews.create(
            commit=False,
            project_id=project_id,
            episode_id=episode_id,
            stage_task_id=payload.stage_task_id,
            reviewer_user_id=None,
            decision=payload.decision,
            comment_text=payload.decision_note,
            payload_jsonb={
                "source": "workspace-review-form",
                "task_status_at_review": stage_task.task_status,
            },
        )
        self.stage_tasks.update_review_status(payload.stage_task_id, payload.decision, commit=False)

        self.db.commit()
        self.db.refresh(review)
        return review
