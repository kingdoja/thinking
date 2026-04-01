from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.schemas.workspace import SubmitReviewDecisionRequest
from app.services.review_service import ReviewService


class FakeDb:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.refreshed = []

    def commit(self) -> None:
        self.commit_calls += 1

    def refresh(self, obj) -> None:
        self.refreshed.append(obj)


class FakeStageTaskRepository:
    def __init__(self, stage_task) -> None:
        self.stage_task = stage_task
        self.updated = []

    def get(self, task_id):
        if self.stage_task and self.stage_task.id == task_id:
            return self.stage_task
        return None

    def update_review_status(self, task_id, review_status: str, commit: bool = True):
        task = self.get(task_id)
        if task is None:
            return None
        task.review_status = review_status
        self.updated.append((task_id, review_status, commit))
        return task


class FakeReviewRepository:
    def __init__(self) -> None:
        self.created = []

    def create(self, commit: bool = True, **kwargs):
        review = SimpleNamespace(
            id=uuid4(),
            created_at=None,
            **kwargs,
        )
        self.created.append((commit, review))
        return review


def make_stage_task(**overrides):
    defaults = {
        "id": uuid4(),
        "project_id": uuid4(),
        "episode_id": uuid4(),
        "review_required": True,
        "task_status": "succeeded",
        "review_status": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_submit_review_decision_updates_stage_task_and_creates_review():
    stage_task = make_stage_task()
    db = FakeDb()
    stage_tasks = FakeStageTaskRepository(stage_task)
    reviews = FakeReviewRepository()
    service = ReviewService(db, stage_tasks, reviews)
    payload = SubmitReviewDecisionRequest(
        stage_task_id=stage_task.id,
        decision="approved",
        decision_note="Looks good",
    )

    review = service.submit_review_decision(stage_task.project_id, stage_task.episode_id, payload)

    assert review.decision == "approved"
    assert review.comment_text == "Looks good"
    assert stage_task.review_status == "approved"
    assert stage_tasks.updated == [(stage_task.id, "approved", False)]
    assert reviews.created[0][0] is False
    assert db.commit_calls == 1
    assert db.refreshed == [review]


def test_submit_review_decision_rejects_stage_task_without_review_gate():
    stage_task = make_stage_task(review_required=False)
    db = FakeDb()
    service = ReviewService(db, FakeStageTaskRepository(stage_task), FakeReviewRepository())
    payload = SubmitReviewDecisionRequest(stage_task_id=stage_task.id, decision="approved")

    with pytest.raises(ValueError, match="does not require review"):
        service.submit_review_decision(stage_task.project_id, stage_task.episode_id, payload)

    assert db.commit_calls == 0


def test_submit_review_decision_requires_existing_stage_task():
    db = FakeDb()
    service = ReviewService(db, FakeStageTaskRepository(None), FakeReviewRepository())
    payload = SubmitReviewDecisionRequest(stage_task_id=uuid4(), decision="approved")

    with pytest.raises(LookupError, match="Stage task not found"):
        service.submit_review_decision(uuid4(), uuid4(), payload)

    assert db.commit_calls == 0
