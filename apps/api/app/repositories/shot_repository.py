from typing import List, Dict, Any, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ShotModel


class ShotRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_many(self, payloads: List[Dict[str, Any]], commit: bool = True) -> List[ShotModel]:
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

    def list_for_episode(self, episode_id) -> List[ShotModel]:
        stmt = (
            select(ShotModel)
            .where(ShotModel.episode_id == episode_id)
            .order_by(ShotModel.version.desc(), ShotModel.scene_no.asc(), ShotModel.shot_no.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_current_for_episode(self, episode_id) -> List[ShotModel]:
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

    def list_for_stage_task(self, stage_task_id) -> List[ShotModel]:
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

    def get_by_id(self, shot_id) -> Optional[ShotModel]:
        """Get a single shot by ID."""
        return self.db.get(ShotModel, shot_id)

    def get_by_id_and_version(self, shot_id, version: int) -> Optional[ShotModel]:
        """Get a specific version of a shot."""
        stmt = select(ShotModel).where(
            ShotModel.id == shot_id,
            ShotModel.version == version
        )
        return self.db.scalar(stmt)

    def list_versions_for_shot(self, shot_id) -> List[ShotModel]:
        """Get all versions of a shot, ordered by version descending."""
        stmt = (
            select(ShotModel)
            .where(ShotModel.id == shot_id)
            .order_by(ShotModel.version.desc())
        )
        return list(self.db.scalars(stmt).all())

    def create_shot(self, payload: Dict[str, Any], commit: bool = True) -> ShotModel:
        """Create a single shot."""
        shot = ShotModel(**payload)
        self.db.add(shot)
        if commit:
            self.db.commit()
            self.db.refresh(shot)
        else:
            self.db.flush()
        return shot
