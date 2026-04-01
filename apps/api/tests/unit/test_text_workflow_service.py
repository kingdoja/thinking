from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.services.text_workflow_service import TEXT_STAGE_SEQUENCE, TextWorkflowService


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshed = []

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, obj) -> None:
        self.refreshed.append(obj)


class FakeStageTaskRepository:
    def __init__(self) -> None:
        self.created = []

    def create(self, commit: bool = True, **kwargs):
        task = SimpleNamespace(id=uuid4(), **kwargs)
        self.created.append((commit, task))
        return task


class FakeDocumentRepository:
    def __init__(self, existing_versions=None) -> None:
        self.existing_versions = existing_versions or {}
        self.created = []

    def latest_version_for_episode_and_type(self, episode_id, document_type: str) -> int:
        return self.existing_versions.get(document_type, 0)

    def create(self, commit: bool = True, **kwargs):
        document = SimpleNamespace(id=uuid4(), **kwargs)
        self.created.append((commit, document))
        self.existing_versions[document.document_type] = document.version
        return document


class FakeShotRepository:
    def __init__(self, version: int = 0) -> None:
        self.version = version
        self.created_batches = []

    def latest_version_for_episode(self, episode_id) -> int:
        return self.version

    def create_many(self, payloads: list[dict], commit: bool = True):
        shots = [SimpleNamespace(id=uuid4(), **payload) for payload in payloads]
        self.created_batches.append((commit, shots))
        if shots:
            self.version = shots[0].version
        return shots


class FakeEpisodeRepository:
    def __init__(self) -> None:
        self.updated = []

    def update_progress(self, episode_id, commit: bool = True, **updates):
        self.updated.append((episode_id, commit, updates))
        return SimpleNamespace(id=episode_id, **updates)


class FakeWorkflowRepository:
    def __init__(self) -> None:
        self.updated = []

    def update_status(self, workflow_id, status: str, commit: bool = True, **updates):
        self.updated.append((workflow_id, status, commit, updates))
        return SimpleNamespace(id=workflow_id, status=status, **updates)


def make_project():
    return SimpleNamespace(
        id=uuid4(),
        name="演示项目：她不是弃女",
        genre="女频逆袭",
        target_platform="douyin",
        target_audience="18-30 女性向短剧用户",
        brief_version=0,
    )


def make_episode():
    return SimpleNamespace(
        id=uuid4(),
        episode_no=1,
        title="EP01 她不是弃女",
        target_duration_sec=73,
        script_version=0,
        storyboard_version=0,
        visual_version=0,
    )


def make_workflow(project_id, episode_id):
    return SimpleNamespace(id=uuid4(), project_id=project_id, episode_id=episode_id, status="running")


def test_execute_text_chain_creates_stage_tasks_documents_and_shots():
    project = make_project()
    episode = make_episode()
    workflow = make_workflow(project.id, episode.id)
    db = FakeDb()
    stage_tasks = FakeStageTaskRepository()
    documents = FakeDocumentRepository()
    shots = FakeShotRepository(version=0)
    episodes = FakeEpisodeRepository()
    workflows = FakeWorkflowRepository()
    service = TextWorkflowService(db, stage_tasks, documents, shots, episodes, workflows)

    result = service.execute_text_chain(project, episode, workflow, "brief")

    assert [task.stage_type for _, task in stage_tasks.created] == TEXT_STAGE_SEQUENCE
    assert [doc.document_type for _, doc in documents.created] == [
        "brief",
        "story_bible",
        "character_profile",
        "script_draft",
        "visual_spec",
    ]
    assert len(shots.created_batches) == 1
    assert len(shots.created_batches[0][1]) == 3
    assert result["workflow_status"] == "waiting_review"
    assert workflows.updated[0][1] == "waiting_review"
    assert episodes.updated[0][2]["current_stage"] == "storyboard"
    assert episodes.updated[0][2]["status"] == "storyboard_ready"
    assert episodes.updated[0][2]["script_version"] == 1
    assert episodes.updated[0][2]["storyboard_version"] == 1


def test_execute_text_chain_respects_start_stage_and_versions():
    project = make_project()
    episode = make_episode()
    workflow = make_workflow(project.id, episode.id)
    db = FakeDb()
    stage_tasks = FakeStageTaskRepository()
    documents = FakeDocumentRepository({"script_draft": 2, "visual_spec": 4})
    shots = FakeShotRepository(version=3)
    episodes = FakeEpisodeRepository()
    workflows = FakeWorkflowRepository()
    service = TextWorkflowService(db, stage_tasks, documents, shots, episodes, workflows)

    service.execute_text_chain(project, episode, workflow, "script")

    assert [task.stage_type for _, task in stage_tasks.created] == ["script", "storyboard"]
    assert [doc.document_type for _, doc in documents.created] == ["script_draft", "visual_spec"]
    assert documents.created[0][1].version == 3
    assert documents.created[1][1].version == 5
    assert shots.created_batches[0][1][0].version == 4
    assert episodes.updated[0][2]["script_version"] == 3
    assert episodes.updated[0][2]["storyboard_version"] == 4
