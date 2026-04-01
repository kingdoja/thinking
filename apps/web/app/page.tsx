import Link from "next/link";

import { getDemoWorkspaceHref } from "../lib/api";

const quickLinks = [
  { label: "Overview", href: "#overview", active: true },
  { label: "Project Status", href: "#project-status" },
  { label: "Real Workspace", href: getDemoWorkspaceHref() },
  { label: "Integration Guide", href: "#integration-guide" },
];

const shots = [
  { code: "SHOT_01", label: "女主首次登场，身份反差建立", duration: "6s" },
  { code: "SHOT_02", label: "冲突抬升，反派正面施压", duration: "5s" },
  { code: "SHOT_03", label: "伏笔回收，进入下一段悬念", duration: "7s" },
];

const nextSteps = [
  "把首页 CTA 全部换成真实入口，不再保留无行为按钮。",
  "继续把 Workspace 页面从只读状态升级到可触发 workflow / review / rerun。",
  "补齐文本主链路的 stage 执行与 document 写回，先跑通到 storyboard。",
  "补一套 API smoke 和前端联调清单，保证 demo 不靠手工改数据。",
];

export default function HomePage() {
  const demoWorkspaceHref = getDemoWorkspaceHref();

  return (
    <main className="shell">
      <div className="topbar">
        <div>
          <div className="badge">Editorial Control Room</div>
          <h1 className="section-title" style={{ marginTop: 12 }}>
            AI 漫剧创作者工作台
          </h1>
          <p className="subtle">
            把女频网文或短剧脚本素材，改编成可发布的竖屏漫剧单集包。
          </p>
        </div>
        <Link className="btn primary" href={demoWorkspaceHref}>
          进入真实工作台
        </Link>
      </div>

      <section className="hero" id="overview">
        <article className="panel hero-card">
          <div className="mono">PHASE 1 / MVP WORKSPACE</div>
          <h2 className="section-title" style={{ fontSize: 34, marginTop: 10 }}>
            先把单集包的真实骨架跑通
          </h2>
          <p className="subtle">
            现在这套仓库已经有文档、数据模型、workspace 聚合接口和真实的工作台路由。首页仍然保留产品展示壳，真正的数据联调入口已经迁移到独立的 workspace 页面。
          </p>
          <div className="action-row">
            <Link className="btn primary" href={demoWorkspaceHref}>
              查看真实 Workspace
            </Link>
            <a className="btn" href="#project-status">
              查看项目进度
            </a>
            <a className="btn" href="#integration-guide">
              查看联调说明
            </a>
          </div>
        </article>

        <article className="panel hero-card preview-well">
          <div className="mono">9:16 PREVIEW STAGE / EP01</div>
          <div className="phone">
            <div>
              <h3 className="phone-title">她不是弃女</h3>
              <div className="phone-sub">73 秒 · 配音 v2 · QA 待确认</div>
            </div>
          </div>
        </article>
      </section>

      <section className="grid">
        <aside className="panel sidebar">
          <div className="mono">PAGE NAV</div>
          <div className="sidebar-nav">
            {quickLinks.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className={item.active ? "sidebar-item active" : "sidebar-item"}
                style={{ display: "block" }}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </aside>

        <section className="panel main">
          <div className="stagebar">
            <span className="done" />
            <span className="done" />
            <span className="active" />
            <span />
            <span />
          </div>
          <div className="mono">CURRENT STAGE / STORYBOARD</div>
          <h2 className="section-title" style={{ fontSize: 26, marginTop: 10 }}>
            当前阶段：真实 Workspace 已接通
          </h2>
          <p className="subtle" style={{ marginBottom: 18 }}>
            首页还是演示壳，但真实数据已经从后端 workspace 聚合接口返回。接下来优先做的是把 workflow 操作、review 动作和 rerun 入口接到这套真实数据链上。
          </p>
          <div className="storyboard-grid">
            {shots.map((shot) => (
              <article key={shot.code} className="shot-card">
                <div className="shot-thumb" />
                <div className="shot-meta">
                  <strong>{shot.code}</strong>
                  <div className="subtle" style={{ marginTop: 6 }}>
                    {shot.label}
                  </div>
                  <div className="mono" style={{ marginTop: 10 }}>
                    {shot.duration} / READY FOR RENDER
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        <aside className="panel assist">
          <div className="mono">AI ASSIST + QA</div>
          <div className="kpi" style={{ marginTop: 16 }}>
            <div className="kpi-card">
              <strong>当前判断</strong>
              <div className="subtle" style={{ marginTop: 6 }}>
                项目整体在 Iteration 1 收尾、准备进入 Iteration 2 的位置。
              </div>
            </div>
            <div className="kpi-card">
              <strong>主要缺口</strong>
              <div className="subtle" style={{ marginTop: 6 }}>
                前端交互仍偏静态，workflow start、审核、重跑和编辑能力还没真正接上。
              </div>
            </div>
            <div className="kpi-card">
              <strong>现在先做</strong>
              <div className="subtle" style={{ marginTop: 6 }}>
                优先进入真实 workspace，确认 stage、shots、review、QA 聚合结果是否正常。
              </div>
            </div>
          </div>
        </aside>
      </section>

      <section id="project-status" className="panel hero-card" style={{ marginTop: 18 }}>
        <div className="mono">PROJECT STATUS</div>
        <h2 className="section-title" style={{ fontSize: 26, marginTop: 10 }}>
          目前做到哪一步了
        </h2>
        <div className="kpi" style={{ marginTop: 18 }}>
          <div className="kpi-card">
            <strong>已完成</strong>
            <div className="subtle" style={{ marginTop: 6 }}>
              Monorepo、设计稿、MVP 文档、数据库模型、workspace 聚合 API、独立 workspace 页面都已经落下来了。
            </div>
          </div>
          <div className="kpi-card">
            <strong>进行中</strong>
            <div className="subtle" style={{ marginTop: 6 }}>
              首页仍是展示壳，真实工作流操作还没有打通到前端，所以你会感觉“能开，但像 demo”。
            </div>
          </div>
          <div className="kpi-card">
            <strong>下一里程碑</strong>
            <div className="subtle" style={{ marginTop: 6 }}>
              跑通素材到 storyboard 的文本主链路，让工作台不止能看状态，还能真正推进状态。
            </div>
          </div>
        </div>
      </section>

      <section id="integration-guide" className="panel hero-card" style={{ marginTop: 18 }}>
        <div className="mono">NEXT ACTIONS</div>
        <h2 className="section-title" style={{ fontSize: 26, marginTop: 10 }}>
          你接下来该怎么推进
        </h2>
        <div className="kpi" style={{ marginTop: 18 }}>
          {nextSteps.map((item) => (
            <div key={item} className="kpi-card">
              <div className="subtle">{item}</div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
