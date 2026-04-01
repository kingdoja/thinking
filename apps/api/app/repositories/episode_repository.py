from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EpisodeModel
from app.schemas.project import CreateEpisodeRequest


class EpisodeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, project_id, payload: CreateEpisodeRequest) -> EpisodeModel:
        episode = EpisodeModel(
            project_id=project_id,
            episode_no=payload.episode_no,
            title=payload.title,
            target_duration_sec=payload.target_duration_sec,
        )
        self.db.add(episode)
        self.db.commit()
        self.db.refresh(episode)
        return episode

    def get(self, episode_id):
        return self.db.get(EpisodeModel, episode_id)

    def list_for_project(self, project_id) -> list[EpisodeModel]:
        stmt = select(EpisodeModel).where(EpisodeModel.project_id == project_id).order_by(EpisodeModel.episode_no.asc())
        return list(self.db.scalars(stmt).all())

    def update_progress(self, episode_id, commit: bool = True, **updates):
        episode = self.get(episode_id)
        if episode is None:
            return None

        for key, value in updates.items():
            setattr(episode, key, value)

        self.db.add(episode)
        if commit:
            self.db.commit()
            self.db.refresh(episode)
        else:
            self.db.flush()
        return episode
