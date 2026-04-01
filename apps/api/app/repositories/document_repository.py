from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import DocumentModel


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, commit: bool = True, **kwargs) -> DocumentModel:
        document = DocumentModel(**kwargs)
        self.db.add(document)
        if commit:
            self.db.commit()
            self.db.refresh(document)
        else:
            self.db.flush()
        return document

    def list_for_episode(self, episode_id) -> list[DocumentModel]:
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.episode_id == episode_id)
            .order_by(DocumentModel.updated_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def latest_version_for_episode_and_type(self, episode_id, document_type: str) -> int:
        version = self.db.scalar(
            select(func.max(DocumentModel.version)).where(
                DocumentModel.episode_id == episode_id,
                DocumentModel.document_type == document_type,
            )
        )
        return int(version or 0)
