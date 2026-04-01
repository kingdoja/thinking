from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_store
from app.schemas.common import SuccessEnvelope
from app.schemas.project import CreateEpisodeRequest, CreateProjectRequest
from app.schemas.workflow import RerunStageRequest, StartEpisodeWorkflowRequest
from app.schemas.workspace import SubmitReviewDecisionRequest
from app.services.store import DatabaseStore

router = APIRouter(prefix="/api", tags=["projects"])


@router.post("/projects", response_model=SuccessEnvelope)
def create_project(payload: CreateProjectRequest, store: DatabaseStore = Depends(get_store)) -> SuccessEnvelope:
    return SuccessEnvelope(data=store.create_project(payload))


@router.get("/projects", response_model=SuccessEnvelope)
def list_projects(store: DatabaseStore = Depends(get_store)) -> SuccessEnvelope:
    return SuccessEnvelope(data=store.list_projects())


@router.get("/projects/{project_id}", response_model=SuccessEnvelope)
def get_project(project_id: UUID, store: DatabaseStore = Depends(get_store)) -> SuccessEnvelope:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return SuccessEnvelope(data=project)


@router.post("/projects/{project_id}/episodes", response_model=SuccessEnvelope)
def create_episode(project_id: UUID, payload: CreateEpisodeRequest, store: DatabaseStore = Depends(get_store)) -> SuccessEnvelope:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return SuccessEnvelope(data=store.create_episode(project_id, payload))


@router.get("/projects/{project_id}/episodes/{episode_id}", response_model=SuccessEnvelope)
def get_episode(project_id: UUID, episode_id: UUID, store: DatabaseStore = Depends(get_store)) -> SuccessEnvelope:
    episode = store.get_episode(episode_id)
    if not episode or str(episode.project_id) != str(project_id):
        raise HTTPException(status_code=404, detail="Episode not found")
    return SuccessEnvelope(data=episode)


@router.get("/projects/{project_id}/episodes/{episode_id}/workspace", response_model=SuccessEnvelope)
def get_workspace(project_id: UUID, episode_id: UUID, store: DatabaseStore = Depends(get_store)) -> SuccessEnvelope:
    workspace = store.build_workspace(project_id, episode_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return SuccessEnvelope(data=workspace)


@router.post("/projects/{project_id}/episodes/{episode_id}/workflow/start", response_model=SuccessEnvelope)
def start_workflow(project_id: UUID, episode_id: UUID, payload: StartEpisodeWorkflowRequest, store: DatabaseStore = Depends(get_store)) -> SuccessEnvelope:
    project = store.get_project(project_id)
    episode = store.get_episode(episode_id)
    if not project or not episode:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return SuccessEnvelope(data=store.start_workflow(project_id, episode_id, payload))


@router.get("/projects/{project_id}/episodes/{episode_id}/workflow", response_model=SuccessEnvelope)
def get_workflow(project_id: UUID, episode_id: UUID, store: DatabaseStore = Depends(get_store)) -> SuccessEnvelope:
    return SuccessEnvelope(data=store.latest_workflow_for_episode(episode_id))


@router.post("/projects/{project_id}/episodes/{episode_id}/workflow/rerun", response_model=SuccessEnvelope)
def rerun_stage(project_id: UUID, episode_id: UUID, payload: RerunStageRequest, store: DatabaseStore = Depends(get_store)) -> SuccessEnvelope:
    return SuccessEnvelope(data={
        "project_id": project_id,
        "episode_id": episode_id,
        "rerun_stage": payload.rerun_stage,
        "target_shot_ids": payload.target_shot_ids,
        "status": "accepted",
    })


@router.post("/projects/{project_id}/episodes/{episode_id}/review", response_model=SuccessEnvelope)
def submit_review(project_id: UUID, episode_id: UUID, payload: SubmitReviewDecisionRequest, store: DatabaseStore = Depends(get_store)) -> SuccessEnvelope:
    project = store.get_project(project_id)
    episode = store.get_episode(episode_id)
    if not project or not episode:
        raise HTTPException(status_code=404, detail="Workspace not found")

    try:
        review = store.submit_review_decision(project_id, episode_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SuccessEnvelope(data=review)
