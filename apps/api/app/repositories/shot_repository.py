from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ShotModel


class ShotRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_many(self, payloads: list[dict], commit: bool = True) -> list[ShotModel]:
        shots = [ShotModel(**payload) for payload in payloads]
        self.db.add_all(shots)
        if commit:
            self.db.commit()
            for shot in shots:
                self.db.refresh(shot)
        else:
            self.db.flush()
        return shots

    def latest_version_for_episode(self, episode_id) -> int:
        version = self.db.scalar(select(func.max(ShotModel.version)).where(ShotModel.episode_id == episode_id))
        return int(version or 0)

    def list_for_episode(self, episode_id) -> list[ShotModel]:
        stmt = (
            select(ShotModel)
            .where(ShotModel.episode_id == episode_id)
            .order_by(ShotModel.version.desc(), ShotModel.scene_no.asc(), ShotModel.shot_no.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_current_for_episode(self, episode_id) -> list[ShotModel]:
        latest_version = self.db.scalar(
            select(func.max(ShotModel.version)).where(ShotModel.episode_id == episode_id)
        )
        if latest_version is None:
            return []

        stmt = (
            select(ShotModel)
            .where(
                ShotModel.episode_id == episode_id,
                ShotModel.version == latest_version,
            )
            .order_by(ShotModel.scene_no.asc(), ShotModel.shot_no.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_for_stage_task(self, stage_task_id) -> list[ShotModel]:
        stmt = (
            select(ShotModel)
            .where(ShotModel.stage_task_id == stage_task_id)
            .order_by(ShotModel.scene_no.asc(), ShotModel.shot_no.asc())
        )
        return list(self.db.scalars(stmt).all())

    def delete_for_stage_task(self, stage_task_id) -> int:
        shots = self.list_for_stage_task(stage_task_id)
        deleted = len(shots)
        for shot in shots:
            self.db.delete(shot)
        self.db.commit()
        return deleted
