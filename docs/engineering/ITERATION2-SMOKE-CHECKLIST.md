# ITERATION 2 SMOKE CHECKLIST

状态：Active  
日期：2026-04-01  
适用范围：文本主链路、workspace 可操作动作、联调 smoke

## 1. 目的

这份清单用于验证当前已经打通的 Iteration 2 能力是否可重复运行，而不是依赖手工改库：

1. `workspace` 能返回真实 project / episode / stage_tasks / documents / shots / review / qa
2. `workflow/start` 从文本阶段启动后，会真实落库文本链路产物
3. `review submit` 会真实写入 `review_decisions` 并同步更新 `StageTask.review_status`
4. `workflow/rerun` 已经接通真实接口，当前阶段返回 `accepted`

当前推荐的 smoke 方式是优先走 API 自举项目与集，不强依赖 demo seed。  
如果你需要固定 workspace URL，再走 demo seed 路径。

## 2. 当前真实能力

截至 2026-04-01，以下链路已经落地：

1. 首页 CTA 可以进入真实 workspace，不再只是 demo 文案
2. workspace 前端支持 `start workflow`、`submit review`、`rerun`
3. 文本主链路支持从 `brief / story_bible / character / script / storyboard` 任一点启动
4. 文本主链路会真实创建：
   `StageTask`
   `Document`
   `Shot`
5. 启动文本链路后，workflow 会进入 `waiting_review`
6. `review submit` 是真实写库，不再是 mock

当前仍然是已知限制：

1. `workflow/rerun` 现在只返回 `accepted`，还没有真正执行重跑链路
2. 如果本机没有 PostgreSQL / API 运行环境，无法做完整集成验证

## 3. 前置条件

### 必需条件

1. API 可以访问，例如 `http://127.0.0.1:8000`
2. API 已连接可写数据库
3. 数据库 schema 已应用到当前版本

### 可选条件

1. 如果要走固定 demo workspace 路径，需要先执行 `scripts/demo_seed.sql`
2. 如果本机使用 Docker，本项目旧的 infra 启动方式仍可继续使用

## 4. 推荐路径：API 自举 smoke

仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke-workspace.ps1
```

默认行为：

1. 检查 `GET /api/health`
2. 通过 API 创建一个临时 smoke project
3. 通过 API 创建一个临时 smoke episode
4. 调用 `POST /workflow/start`，默认从 `brief` 启动
5. 校验 workspace 中是否已经出现真实 `stage_tasks / documents / shots`
6. 调用 `POST /review`
7. 校验 `review_summary` 是否更新
8. 调用 `POST /workflow/rerun`
9. 校验返回 `accepted`

如果要从别的文本阶段开始，例如 `script`：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke-workspace.ps1 -StartStage script
```

## 5. 固定 demo workspace 路径

如果你需要验证固定 workspace URL 或前端 demo 入口，先准备 demo 数据，再复用同一个 smoke 脚本。

### 5.1 准备 demo 数据

使用你当前的 PostgreSQL 方式执行：

```powershell
Get-Content scripts/demo_seed.sql -Raw | psql <your-connection-args>
```

或者沿用项目原来的 Docker 容器方式：

```powershell
Get-Content scripts/demo_seed.sql -Raw |
  docker exec -i thinking-postgres-1 psql -U postgres -d thinking
```

固定 ID：

1. `project_id = 11111111-1111-1111-1111-111111111111`
2. `episode_id = 22222222-2222-2222-2222-222222222222`

### 5.2 复用 smoke 脚本

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke-workspace.ps1 `
  -ProjectId 11111111-1111-1111-1111-111111111111 `
  -EpisodeId 22222222-2222-2222-2222-222222222222 `
  -StartStage brief
```

## 6. 预期结果

执行 smoke 后，应该看到：

1. workspace 返回真实 `latest_workflow`
2. `latest_workflow.status = waiting_review`
3. `stage_tasks` 至少覆盖：
   `brief -> story_bible -> character -> script -> storyboard`
   如果从中间阶段启动，则覆盖该阶段及其后续阶段
4. `documents` 至少覆盖：
   `brief`
   `story_bible`
   `character_profile`
   `script_draft`
   `visual_spec`
5. `shots` 至少生成 3 条
6. `review submit` 后，`latest_decision` 会更新
7. `review_summary.pending_count` 会比提交前减少 1
8. `workflow/rerun` 返回 `accepted`

## 7. 手工补充检查

如果你要做前端联调，再补两步：

1. 打开首页，确认 CTA 能进入真实 workspace
2. 在 workspace 页面手动点击：
   `Start Workflow`
   `Submit Review`
   `Submit Rerun`

预期：

1. 按钮不再是纯 demo 占位
2. 点击后页面会刷新
3. 页面反馈区会显示成功或错误信息

## 8. 已知限制与阻塞

当前这台机器上已经确认过的环境阻塞：

1. 没有 `docker`
2. 没有 `psql`
3. 本地没有运行中的 PostgreSQL / API
4. `py310` 环境缺少 `psycopg`

所以当前仓库内已经完成的是：

1. 代码层实现
2. 单元测试验证
3. 前端 build 验证

真正的本地全链路集成 smoke，需要在具备数据库和 API 运行条件的机器上执行本清单。