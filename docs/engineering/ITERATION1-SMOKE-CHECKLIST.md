# ITERATION 1 SMOKE CHECKLIST

状态：Legacy / Superseded  
日期：2026-03-31  
适用范围：PR-1 ~ PR-4 本地数据库与 workspace 验证

> 最新 smoke 联调入口请优先使用 [ITERATION2-SMOKE-CHECKLIST.md](/d:/ai应用项目/thinking/docs/engineering/ITERATION2-SMOKE-CHECKLIST.md)。
> 这份文档保留为 Iteration 1 历史记录，不再覆盖当前的 `review submit`、文本主链路落库、以及 workspace 可操作动作。
## 1. 文档目的

这份清单用于验证当前已经完成的四个阶段是否真正打通：

1. PR-1：`StageTask / Shot / ReviewDecision` 模型与 migration
2. PR-2：repository + workspace DTO
3. PR-3：`start_workflow -> StageTask` 真写入
4. PR-4：workspace 真实聚合

它的目标不是跑完整产品链路，而是确认：

1. 数据库 schema 已经完整
2. demo 数据可以稳定落库
3. workspace API 能返回真实数据
4. 当前前端接入前，后端聚合已经可信

---

## 2. 预期验证结果

完成本清单后，应该能够确认：

1. 数据库里存在 `projects / episodes / workflow_runs / stage_tasks / documents / shots / assets / qa_reports / review_decisions`
2. `start_workflow` 会新建 `WorkflowRun` 和首个 `StageTask`
3. `GET workspace` 返回真实 `stage_tasks`
4. `GET workspace` 返回真实 `shots`
5. `GET workspace` 返回真实 `review_summary`
6. `GET workspace` 返回优先选中的 `assets`

---

## 3. 前置条件

### 基础环境

1. Docker Desktop 已启动
2. PostgreSQL 容器可用
3. API 所需环境变量已配置
4. `003_iteration1_shots_reviews.sql` 已存在
5. `scripts/demo_seed.sql` 已存在

### 当前关键文件

1. [001_initial_schema.sql](/d:/ai应用项目/thinking/infra/migrations/001_initial_schema.sql)
2. [002_documents_assets_qa.sql](/d:/ai应用项目/thinking/infra/migrations/002_documents_assets_qa.sql)
3. [003_iteration1_shots_reviews.sql](/d:/ai应用项目/thinking/infra/migrations/003_iteration1_shots_reviews.sql)
4. [demo_seed.sql](/d:/ai应用项目/thinking/scripts/demo_seed.sql)

---

## 4. 启动基础设施

在仓库根目录执行：

```powershell
docker compose -f infra/docker/docker-compose.yml up -d postgres redis minio temporal temporal-ui
```

检查 PostgreSQL 是否已启动：

```powershell
docker compose -f infra/docker/docker-compose.yml ps
```

预期：`postgres` 状态为 `running`。

---

## 5. 应用数据库 schema

按顺序执行三个 migration。

### 5.1 执行 001

```powershell
Get-Content infra/migrations/001_initial_schema.sql -Raw |
  docker exec -i thinking-postgres-1 psql -U postgres -d thinking
```

### 5.2 执行 002

```powershell
Get-Content infra/migrations/002_documents_assets_qa.sql -Raw |
  docker exec -i thinking-postgres-1 psql -U postgres -d thinking
```

### 5.3 执行 003

```powershell
Get-Content infra/migrations/003_iteration1_shots_reviews.sql -Raw |
  docker exec -i thinking-postgres-1 psql -U postgres -d thinking
```

如果你的容器名不是 `thinking-postgres-1`，先运行：

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}"
```

然后把上面命令里的容器名替换成你的实际值。

---

## 6. 写入演示数据

执行：

```powershell
Get-Content scripts/demo_seed.sql -Raw |
  docker exec -i thinking-postgres-1 psql -U postgres -d thinking
```

预期：

1. SQL 执行成功
2. 无外键报错
3. 无唯一约束报错

这份 seed 是可重复执行的；它会先删掉同一批演示 ID，再重新插入。

---

## 7. 数据库快速检查

### 7.1 检查核心表计数

```powershell
@"
SELECT 'projects' AS table_name, COUNT(*) FROM projects
UNION ALL
SELECT 'episodes', COUNT(*) FROM episodes
UNION ALL
SELECT 'workflow_runs', COUNT(*) FROM workflow_runs
UNION ALL
SELECT 'stage_tasks', COUNT(*) FROM stage_tasks
UNION ALL
SELECT 'documents', COUNT(*) FROM documents
UNION ALL
SELECT 'shots', COUNT(*) FROM shots
UNION ALL
SELECT 'assets', COUNT(*) FROM assets
UNION ALL
SELECT 'qa_reports', COUNT(*) FROM qa_reports
UNION ALL
SELECT 'review_decisions', COUNT(*) FROM review_decisions;
"@ | docker exec -i thinking-postgres-1 psql -U postgres -d thinking
```

预期最少存在：

1. 1 个 project
2. 1 个 episode
3. 1 个 workflow_run
4. 3 个 stage_tasks
5. 3 个 shots
6. 1 个 review_decision

### 7.2 检查 stage_tasks

```powershell
@"
SELECT stage_type, task_status, review_required, review_status
FROM stage_tasks
WHERE workflow_run_id = '33333333-3333-3333-3333-333333333333'::uuid
ORDER BY created_at;
"@ | docker exec -i thinking-postgres-1 psql -U postgres -d thinking
```

预期：

1. `brief` 为 `succeeded`
2. `script` 为 `succeeded`
3. `storyboard` 为 `succeeded`
4. `storyboard.review_status` 为 `pending`

### 7.3 检查 shots

```powershell
@"
SELECT shot_code, scene_no, shot_no, status, version
FROM shots
WHERE episode_id = '22222222-2222-2222-2222-222222222222'::uuid
ORDER BY scene_no, shot_no;
"@ | docker exec -i thinking-postgres-1 psql -U postgres -d thinking
```

预期：

1. 返回 `SHOT_01`、`SHOT_02`、`SHOT_03`
2. 都属于同一个 version
3. 第三个镜头状态为 `warning`

---

## 8. 启动 API

在仓库根目录或 `apps/api` 对应运行方式下启动 API。

如果你当前是直接用 Python 启动，示例：

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://postgres:postgres@localhost:5432/thinking'
uvicorn apps.api.app.main:app --reload
```

如果项目实际启动入口不同，以当前 API 主入口为准。

---

## 9. API Smoke 验证

### 9.1 查询 workspace

```powershell
Invoke-RestMethod \
  -Method GET \
  -Uri 'http://127.0.0.1:8000/api/projects/11111111-1111-1111-1111-111111111111/episodes/22222222-2222-2222-2222-222222222222/workspace'
```

预期：

1. `data.project.id` 正确
2. `data.episode.id` 正确
3. `data.stage_tasks` 长度至少为 3
4. `data.shots` 长度为 3
5. `data.review_summary.status = pending`
6. `data.metadata.shots_mode = current-version-db-query`

### 9.2 查询 workflow

```powershell
Invoke-RestMethod \
  -Method GET \
  -Uri 'http://127.0.0.1:8000/api/projects/11111111-1111-1111-1111-111111111111/episodes/22222222-2222-2222-2222-222222222222/workflow'
```

预期：

1. `workflow_kind = episode`
2. `status = waiting_review` 或当前实现返回的最新状态

### 9.3 验证 start_workflow 真写入 StageTask

先记录当前 `stage_tasks` 数量，再执行：

```powershell
Invoke-RestMethod \
  -Method POST \
  -Uri 'http://127.0.0.1:8000/api/projects/11111111-1111-1111-1111-111111111111/episodes/22222222-2222-2222-2222-222222222222/workflow/start' \
  -ContentType 'application/json' \
  -Body '{"start_stage":"brief"}'
```

然后再次查询数据库：

```powershell
@"
SELECT stage_type, task_status, created_at
FROM stage_tasks
WHERE episode_id = '22222222-2222-2222-2222-222222222222'::uuid
ORDER BY created_at DESC
LIMIT 3;
"@ | docker exec -i thinking-postgres-1 psql -U postgres -d thinking
```

预期：

1. 多出一条新的 `brief` stage task
2. 对应会新增一条新的 `workflow_run`

---

## 10. 失败排查

### 问题 1：缺表错误

表现：

1. `relation "shots" does not exist`
2. `relation "review_decisions" does not exist`

处理：

1. 确认已执行 `003_iteration1_shots_reviews.sql`
2. 确认执行的数据库是 `thinking`

### 问题 2：workspace 返回空 shots

表现：

1. `data.shots = []`

处理：

1. 确认 `scripts/demo_seed.sql` 已执行成功
2. 确认 `shots.version` 不为空
3. 确认 `episode_id` 匹配

### 问题 3：review summary 不是 pending

表现：

1. `review_summary.status = none`

处理：

1. 确认 `storyboard` 的 `review_required = true`
2. 确认 `storyboard.task_status = succeeded`
3. 确认 `storyboard.review_status = pending` 或 `NULL`

---

## 11. 通过标准

本清单通过，表示当前系统已经具备以下能力：

1. Iteration 1 的数据库核心对象已完整
2. workflow 启动会真实写入 `StageTask`
3. workspace 后端已经基于真实 `shots / stage_tasks / reviews` 聚合
4. 后续可以放心进入前端接入阶段

---

## 12. 下一步建议

完成这份 smoke 后，下一步就可以直接进入：

1. `PR-5 Web Workspace Integration`

因为到这一步，后端聚合和演示数据已经足够支撑前端真实联调。
