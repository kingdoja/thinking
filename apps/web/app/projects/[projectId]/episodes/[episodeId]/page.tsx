import Link from "next/link";

import { fetchEpisodeWorkspace } from "../../../../../lib/api";

type WorkspacePageProps = {
  params: Promise<{
    projectId: string;
    episodeId: string;
  }>;
};

function formatSeconds(durationMs: number): string {
  return `${Math.max(1, Math.round(durationMs / 1000))}s`;
}

function formatStageLabel(stage: string): string {
  return stage.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatTime(value: string | null): string {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default async function WorkspacePage({ params }: WorkspacePageProps) {
  const { projectId, episodeId } = await params;

  try {
    const workspace = await fetchEpisodeWorkspace(projectId, episodeId);
    const activeStageIndex = Math.max(
      0,
      workspace.stage_tasks.findIndex((task) => task.task_status === "running" || task.task_status === "pending"),
    );

    return (
      <main className="shell workspace-shell">
        <div className="topbar">
          <div>
            <div className="badge">Live Workspace</div>
            <h1 className="section-title" style={{ marginTop: 12 }}>
              {workspace.project.name}
            </h1>
            <p className="subtle">
              EP{workspace.episode.episode_no.toString().padStart(2, "0")} · {workspace.episode.title ?? "未命名剧集"} ·
              当前阶段 {formatStageLabel(workspace.episode.current_stage)}
            </p>
          </div>
          <div className="workspace-actions">
            <Link className="btn" href="/">
              返回首页
            </Link>
            <span className="workspace-status-pill">Workflow: {workspace.latest_workflow?.status ?? "idle"}</span>
          </div>
        </div>

        <section className="workspace-hero">
          <article className="panel hero-card">
            <div className="mono">DATABASE-BACKED WORKSPACE</div>
            <h2 className="section-title" style={{ fontSize: 30, marginTop: 10 }}>
              当前工作台已经接上真实聚合结果
            </h2>
            <p className="subtle">
              这里展示的是后端 workspace 接口返回的真实数据，包括 stage task、分镜、QA 摘要和审核状态，不再依赖前端硬编码。
            </p>
            <div className="action-row">
              <div className="kpi-card workspace-hero-card">
                <strong>Shots</strong>
                <div className="subtle" style={{ marginTop: 6 }}>{workspace.shots.length} 个镜头已入库</div>
              </div>
              <div className="kpi-card workspace-hero-card">
                <strong>Review</strong>
                <div className="subtle" style={{ marginTop: 6 }}>
                  {workspace.review_summary.status} / {workspace.review_summary.pending_count} pending
                </div>
              </div>
              <div className="kpi-card workspace-hero-card">
                <strong>QA</strong>
                <div className="subtle" style={{ marginTop: 6 }}>
                  {workspace.qa_summary.result} / {workspace.qa_summary.issue_count} issues
                </div>
              </div>
            </div>
          </article>

          <article className="panel hero-card preview-well workspace-preview-card">
            <div className="mono">CURRENT EXPORT SURFACE</div>
            <div className="phone workspace-phone">
              <div>
                <h3 className="phone-title">{workspace.episode.title ?? "未命名剧集"}</h3>
                <div className="phone-sub">
                  {workspace.episode.target_duration_sec} 秒 · {workspace.assets.length} 条资产 · review {workspace.review_summary.status}
                </div>
              </div>
            </div>
          </article>
        </section>

        <section className="workspace-grid">
          <aside className="panel sidebar workspace-sidebar">
            <div className="mono">WORKFLOW SNAPSHOT</div>
            <div className="sidebar-nav">
              {workspace.stage_tasks.map((task, index) => {
                const stateClass =
                  task.task_status === "succeeded"
                    ? "done"
                    : index === activeStageIndex
                      ? "active"
                      : "idle";

                return (
                  <div key={task.id} className={`workspace-stage-card ${stateClass}`}>
                    <div>
                      <strong>{formatStageLabel(task.stage_type)}</strong>
                      <div className="subtle" style={{ marginTop: 6 }}>
                        {task.worker_kind} · {task.task_status}
                      </div>
                    </div>
                    <div className="workspace-stage-meta">
                      <span>{task.review_required ? `review ${task.review_status ?? "pending"}` : "no review"}</span>
                      <span>{formatTime(task.finished_at ?? task.started_at)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </aside>

          <section className="panel main workspace-main">
            <div className="stagebar workspace-stagebar">
              {workspace.stage_tasks.map((task, index) => {
                const className =
                  task.task_status === "succeeded"
                    ? "done"
                    : index === activeStageIndex
                      ? "active"
                      : "";
                return <span key={task.id} className={className} />;
              })}
            </div>
            <div className="mono">CURRENT SHOTS / STORYBOARD</div>
            <h2 className="section-title" style={{ fontSize: 26, marginTop: 10 }}>当前镜头列表</h2>
            <p className="subtle" style={{ marginBottom: 18 }}>
              分镜区已经改成读取数据库中的最新 shot version。这里可以直接看到镜头状态、时长和镜头文案。
            </p>
            <div className="storyboard-grid">
              {workspace.shots.map((shot) => (
                <article key={shot.id ?? shot.code} className="shot-card">
                  <div className={`shot-thumb shot-thumb-${shot.status}`} />
                  <div className="shot-meta">
                    <strong>
                      {shot.code}
                      {shot.shot_index ? ` / #${shot.shot_index}` : ""}
                    </strong>
                    <div className="subtle" style={{ marginTop: 6 }}>{shot.title ?? "暂无动作描述"}</div>
                    <div className="mono" style={{ marginTop: 10 }}>
                      {formatSeconds(shot.duration_ms)} / {shot.status.toUpperCase()}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <aside className="panel assist workspace-assist">
            <div className="mono">QA + REVIEW</div>
            <div className="kpi" style={{ marginTop: 16 }}>
              <div className="kpi-card">
                <strong>审核状态</strong>
                <div className="subtle" style={{ marginTop: 6 }}>
                  {workspace.review_summary.status}
                  {workspace.review_summary.latest_decision?.decision_note
                    ? ` · ${workspace.review_summary.latest_decision.decision_note}`
                    : " · 暂无最新审核备注"}
                </div>
              </div>
              <div className="kpi-card">
                <strong>QA 摘要</strong>
                <div className="subtle" style={{ marginTop: 6 }}>
                  {workspace.qa_summary.result} · {workspace.qa_summary.issue_count} 个问题
                </div>
              </div>
              <div className="kpi-card">
                <strong>最新资产</strong>
                <div className="subtle" style={{ marginTop: 6 }}>
                  {workspace.assets[0]?.asset_type ?? "暂无资产"}
                  {workspace.assets[0]?.storage_key ? ` · ${workspace.assets[0].storage_key}` : ""}
                </div>
              </div>
            </div>

            <div className="workspace-docs-block">
              <div className="mono">DOCUMENT SNAPSHOT</div>
              <div className="workspace-doc-list">
                {workspace.documents.map((document) => (
                  <div key={document.id} className="workspace-doc-item">
                    <strong>{document.document_type}</strong>
                    <div className="subtle">v{document.version} · {document.status}</div>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </section>
      </main>
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown workspace error";

    return (
      <main className="shell workspace-shell">
        <div className="topbar">
          <div>
            <div className="badge">Workspace Unavailable</div>
            <h1 className="section-title" style={{ marginTop: 12 }}>真实工作台暂时不可用</h1>
            <p className="subtle">请先启动 API，并确认 demo 数据已经写入数据库。</p>
          </div>
          <Link className="btn" href="/">
            返回首页
          </Link>
        </div>

        <section className="panel workspace-error-panel">
          <div className="mono">FETCH ERROR</div>
          <h2 className="section-title" style={{ fontSize: 24, marginTop: 10 }}>无法获取 workspace 聚合结果</h2>
          <p className="subtle">{message}</p>
          <div className="action-row">
            <Link className="btn primary" href="/">
              返回首页查看接入说明
            </Link>
          </div>
        </section>
      </main>
    );
  }
}
