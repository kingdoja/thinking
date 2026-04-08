# AI 漫剧生成平台 - 项目总体设计文档

## 概述

AI 漫剧生成平台是一个基于 Workflow-First 和 Artifact-First 原则设计的 AI 内容生产系统。系统通过多 Agent 协作、工作流编排和媒体处理，实现从原始素材到成品视频的自动化生产流程。

核心设计理念：
- **Workflow First**: 主业务流程由工作流驱动，而不是由 API 或脚本串接
- **Artifact First**: 系统事实来源是结构化产物，不是聊天上下文
- **Runtime Separation**: 文本生成、媒体执行、QA 评估拆成独立 Runtime
- **Explicit State**: 所有状态都显式建模，可追踪、可重跑
- **Human Gate Is Architectural**: 人工审核是工作流的正式节点

## 架构

### 系统全景图

```
┌────────────────────────────────────────────────────────────┐
│                     Web Application                        │
│  Projects | Episodes | Workspace | Storyboard | QA | Export│
└──────────────────────┬─────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼─────────────────────────────────────┐
│                      API Layer                             │
│  Routes | DTOs | Auth | Workspace Aggregation              │
└──────────────────────┬─────────────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────┐
│                   Workflow Layer                           │
│  episode_workflow | rerun_workflow | review_gates | retry  │
└───────┬──────────────┬──────────────┬──────────────────────┘
        │              │              │
        v              v              v
┌───────────────┐ ┌──────────────┐ ┌─────────────────┐
│ Agent Runtime │ │Media Runtime │ │   QA Runtime    │
│ Brief/Script  │ │Image/TTS/Cut │ │ Rule/Semantic   │
└───────────────┘ └──────────────┘ └─────────────────┘
        │              │              │
        └──────────────┴──────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────┐
│                     Data Layer                             │
│  PostgreSQL | Object Storage | Redis | Logs | Versioning   │
└────────────────────────────────────────────────────────────┘
```

### 分层职责

#### 1. Product Layer (Web Application)
- 提供用户界面和交互
- 展示工作流状态和产物
- 管理人工审核和返工动作
- 不直接执行长任务或串业务流程

#### 2. API Layer
- 接收用户命令并校验输入
- 启动工作流和返回聚合 DTO
- 处理轻量同步操作（编辑、锁定、选择资产）
- 不执行长耗时任务或包含工作流逻辑

#### 3. Workflow Layer
- 编排 Stage 执行顺序和管理依赖
- 处理失败重试和状态机推进
- 控制人工审核节点和重跑范围
- 不负责内容生成的具体实现

#### 4. Agent Runtime
- 执行文本型 Stage（brief、script、storyboard 等）
- 读取上下文、组装 Prompt、调用 LLM
- 校验输出并提交 Document 产物
- 不负责工作流推进和审核决策

#### 5. Media Runtime
- 执行媒体型 Stage（image_render、tts、export 等）
- 调用外部 Provider 生成媒体资产
- 上传对象存储并提交 Asset 产物
- 不负责文本规划和业务决策

#### 6. QA Runtime
- 执行规则型和语义型检查
- 聚合 QA 结果并生成报告
- 提供重跑建议
- 不直接修改内容

## 组件和接口

### 核心数据模型

#### Project
```python
class Project:
    id: UUID
    name: str
    genre: str  # 题材
    platform: str  # 目标平台
    target_audience: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
```

#### Episode
```python
class Episode:
    id: UUID
    project_id: UUID
    title: str
    episode_number: int
    source_material: str
    status: EpisodeStatus
    created_at: datetime
    updated_at: datetime
```

#### WorkflowRun
```python
class WorkflowRun:
    id: UUID
    episode_id: UUID
    workflow_type: str  # episode_workflow, rerun_workflow
    status: WorkflowStatus  # created, running, succeeded, failed
    started_at: datetime
    finished_at: datetime
    temporal_workflow_id: str
```

#### StageTask
```python
class StageTask:
    id: UUID
    workflow_run_id: UUID
    stage_type: str  # brief, script, image_render, etc.
    status: StageTaskStatus  # pending, running, succeeded, failed
    attempt_no: int
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    token_usage: int
    error_code: str
    error_message: str
```

#### Document
```python
class Document:
    id: UUID
    episode_id: UUID
    document_type: str  # brief, story_bible, character_profile, etc.
    version: int
    content_jsonb: dict
    locked_fields: list[str]
    created_by: str  # user_id or agent_name
    created_at: datetime
    updated_at: datetime
```

#### Shot
```python
class Shot:
    id: UUID
    episode_id: UUID
    scene_no: int
    shot_no: int
    duration_sec: float
    visual_description: str
    visual_constraints_jsonb: dict  # character_anchors, style, composition
    created_at: datetime
```

#### Asset
```python
class Asset:
    id: UUID
    episode_id: UUID
    shot_id: UUID  # nullable for episode-level assets
    asset_type: str  # keyframe, audio, subtitle, preview, final_video
    file_path: str
    is_selected: bool
    metadata_jsonb: dict
    created_at: datetime
```

#### QAReport
```python
class QAReport:
    id: UUID
    episode_id: UUID
    workflow_run_id: UUID
    issues: list[dict]  # [{severity, category, description, target_ref}]
    overall_status: str  # passed, warning, failed
    rerun_suggestions: list[str]
    created_at: datetime
```

#### ReviewDecision
```python
class ReviewDecision:
    id: UUID
    episode_id: UUID
    workflow_run_id: UUID
    decision: str  # approved, request_changes, rejected
    comments: str
    reviewer_id: str
    created_at: datetime
```

### Agent 流水线接口

#### StageTaskInput
```python
@dataclass
class StageTaskInput:
    episode_id: UUID
    stage_type: str
    input_refs: dict[str, UUID]  # {document_type: document_id}
    locked_fields: dict[str, list[str]]  # {document_type: [field_names]}
    constraints: dict  # platform constraints, style preferences, etc.
```

#### StageTaskOutput
```python
@dataclass
class StageTaskOutput:
    document_refs: dict[str, UUID]  # {document_type: document_id}
    shot_refs: list[UUID]  # for storyboard stage
    asset_refs: list[UUID]  # for media stages
    warnings: list[str]
    metrics: dict  # token_usage, duration_ms, cost, etc.
```

### 7 阶段流水线

```python
class BaseAgent(ABC):
    def execute(self, input: StageTaskInput) -> StageTaskOutput:
        # 1. Loader: 加载输入文档和锁定字段
        context = self.load(input)
        
        # 2. Normalizer: 清理和结构化上下文
        normalized = self.normalize(context)
        
        # 3. Planner: 创建执行计划
        plan = self.plan(normalized)
        
        # 4. Generator: 调用 LLM 生成内容
        generated = self.generate(plan)
        
        # 5. Critic: 自我审查一致性和质量
        critiqued = self.critique(generated, context)
        
        # 6. Validator: 验证 Schema 和约束
        validated = self.validate(critiqued)
        
        # 7. Committer: 持久化到数据库
        output = self.commit(validated, input)
        
        return output
```

### Workspace 聚合接口

```python
class EpisodeWorkspaceResponse:
    project: Project
    episode: Episode
    latest_workflow: WorkflowRun
    documents: dict[str, Document]  # {document_type: latest_document}
    shots: list[Shot]
    selected_assets: dict[UUID, Asset]  # {shot_id: selected_asset}
    stage_tasks: list[StageTask]
    qa_summary: QAReport
    pending_reviews: list[ReviewDecision]
```

## 数据模型

### 状态机

#### Episode 状态机
```
draft → brief_pending → brief_confirmed → bible_ready → 
episode_writing → storyboard_ready → visual_generating → 
audio_ready → cut_ready → qa_approved/needs_revision → 
review_pending → export_ready → published
```

#### WorkflowRun 状态机
```
created → running → waiting_review → succeeded/failed/canceled
```

#### StageTask 状态机
```
pending → running → succeeded/failed/skipped/blocked
```

### 版本控制策略

#### Document 版本控制
- 每次成功提交形成新版本（version 递增）
- 已确认版本不可被静默覆盖
- 编辑和生成都带来源标记（created_by）
- 锁定字段（locked_fields）保护关键内容

#### Asset 版本控制
- 同一 Shot 可存在多个候选资产
- 通过 is_selected 标记主资产
- rerun 默认只影响目标范围，不覆盖其他资产

#### Workflow 版本控制
- 每次启动工作流形成独立 WorkflowRun
- 每次 Stage 执行形成独立 StageTask
- rerun 创建新任务和新结果，不修改旧任务

## 正确性属性

*属性是系统在所有有效执行中应该保持的特征或行为，是人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1: 工作流启动创建记录
*对于任何*剧集，当启动工作流时，系统应该创建一个 WorkflowRun 记录并设置状态为 created
**验证需求**: 需求 2.1

### 属性 2: Stage 执行顺序保持
*对于任何*工作流，Stage 的执行顺序应该严格按照定义的依赖关系进行，不能跳过或乱序
**验证需求**: 需求 2.1

### 属性 3: Stage 完成创建任务记录
*对于任何*Stage 执行，完成时应该创建 StageTask 记录并包含执行时间、状态和产物引用
**验证需求**: 需求 2.3

### 属性 4: 工作流完成更新状态
*对于任何*工作流，当所有 Stage 成功完成时，WorkflowRun 状态应该更新为 succeeded
**验证需求**: 需求 2.5

### 属性 5: 工作流失败保留产物
*对于任何*工作流，当某个 Stage 失败时，已生成的中间产物应该被保留而不是删除
**验证需求**: 需求 2.4

### 属性 6: Brief 包含必需元素
*对于任何*Brief 文档，应该包含 genre、target_audience、core_selling_points、main_conflict 和 target_style 字段
**验证需求**: 需求 3.1

### 属性 7: 文档编辑创建新版本
*对于任何*文档编辑操作，应该创建新版本而不是覆盖原版本，且 version 号递增
**验证需求**: 需求 5.1

### 属性 8: 锁定字段编辑拒绝
*对于任何*包含锁定字段的文档，尝试修改锁定字段应该被拒绝并返回验证错误
**验证需求**: 需求 5.3

### 属性 9: Storyboard 生成 Shot 记录
*对于任何*Storyboard Stage 执行，应该为每个镜头创建 Shot 记录并持久化到数据库
**验证需求**: 需求 3.5, 6.1

### 属性 10: Shot 包含必需字段
*对于任何*Shot 记录，应该包含 shot_no、scene_no、duration_sec、visual_description 和 visual_constraints_jsonb 字段
**验证需求**: 需求 6.2

### 属性 11: Workspace 返回完整聚合
*对于任何*工作台查询，应该返回 project、episode、documents、shots、stage_tasks 的完整聚合信息
**验证需求**: 需求 7.1

### 属性 12: Workspace 返回最新文档版本
*对于任何*工作台查询，返回的文档应该是每种文档类型的最新版本（最大 version 号）
**验证需求**: 需求 7.2

### 属性 13: Agent 执行遵循流水线顺序
*对于任何*Agent 执行，应该严格按照 Loader → Normalizer → Planner → Generator → Critic → Validator → Committer 的顺序执行
**验证需求**: 需求 4.1

### 属性 14: Loader 加载输入引用
*对于任何*Agent 执行，Loader 阶段应该加载 StageTaskInput 中指定的所有输入文档引用
**验证需求**: 需求 4.2

### 属性 15: Generator 调用 LLM
*对于任何*Agent 执行，Generator 阶段应该调用 LLM 服务并获取生成内容
**验证需求**: 需求 4.3

### 属性 16: Validator 校验 Schema
*对于任何*Agent 执行，Validator 阶段应该验证生成内容符合文档类型的 Schema 和必填字段要求
**验证需求**: 需求 4.4

### 属性 17: Committer 持久化并返回引用
*对于任何*Agent 执行，Committer 阶段应该持久化文档到数据库并在 StageTaskOutput 中返回文档引用
**验证需求**: 需求 4.5

### 属性 18: 重跑创建新 WorkflowRun
*对于任何*重跑操作，应该创建新的 WorkflowRun 而不是修改原有的 WorkflowRun
**验证需求**: 需求 12.1

### 属性 19: 重跑保留旧版本产物
*对于任何*重跑操作，应该保留旧版本的文档和资产，新版本与旧版本并存
**验证需求**: 需求 12.3

### 属性 20: QA 失败阻止导出
*对于任何*QA 检查失败的剧集，应该阻止工作流进入导出阶段
**验证需求**: 需求 10.3, 10.4

## 错误处理

### 失败分类

1. **输入失败**: 素材为空、refs 缺失、锁定对象不存在
2. **Provider 失败**: LLM 超时、Image provider 错误、TTS 返回空音频
3. **校验失败**: Schema 不合法、必填字段缺失、Shot 输出不完整
4. **系统失败**: 存储失败、数据库写入失败、工作流中断

### 失败处理原则

1. 每个失败都必须落日志并归属到 StageTask
2. 每个失败都必须可让前端感知状态
3. 失败默认不能静默吞掉
4. Script 失败不覆盖旧版本
5. Image_render 失败不影响其他 Shot
6. QA 失败进入 review 或 revision 状态，不直接推进导出

### 重试策略

- Stage 执行失败自动重试，最多 3 次
- 每次重试创建新的 StageTask 记录（attempt_no 递增）
- 重试间隔采用指数退避策略
- 超过最大重试次数后标记 WorkflowRun 为 failed

## 测试策略

### 单元测试

- 测试每个 Service 的核心逻辑
- 测试 Schema 验证和版本控制
- 测试状态机转换
- 使用 Mock 隔离外部依赖

### Property-Based 测试

- 使用 Hypothesis 框架生成随机测试用例
- 验证上述 20 个正确性属性
- 每个属性至少运行 100 次迭代
- 发现边界条件和极端输入的 bug

### 集成测试

- 测试完整的文本链路（素材 → storyboard）
- 测试完整的媒体链路（visual_spec → preview）
- 测试失败恢复和重跑机制
- 测试人工审核流程

### 端到端测试

- 测试从项目创建到导出的完整流程
- 验证数据库持久化和对象存储
- 验证工作台聚合视图
- 验证前端可以正确消费 API

## 性能考虑

### 响应时间目标

- API 响应（不含 LLM）: < 100ms
- 数据库查询: < 50ms
- Brief 生成: 10-15 秒
- 完整文本链路: 2-3 分钟
- 图像生成: 30-60 秒/张
- 预览合成: 1-2 分钟

### 成本优化

- 默认使用通义千问（性价比最高）
- 完整剧集生成成本: ¥0.05（通义千问）
- 支持根据任务类型选择不同 LLM
- 缓存常用 Prompt 模板

### 并发支持

- 设计支持多用户并发使用
- 使用 Temporal 管理长任务
- 使用 Redis 缓存热数据
- 数据库连接池优化

## 可扩展性

### Provider 适配层

- LLM Adapter: 统一接口支持 Qwen、OpenAI、Claude
- Image Adapter: 支持 Stable Diffusion、DALL-E 等
- TTS Adapter: 支持多种语音合成服务
- Storage Adapter: 支持 S3、OSS 等对象存储

### 插件化 Agent

- 新 Agent 只需继承 BaseAgent 并实现 7 个阶段方法
- Agent 注册到 AgentRegistry
- Workflow 通过 stage_type 动态调用对应 Agent

### 水平扩展

- API 层无状态，可水平扩展
- Temporal Worker 可独立扩展
- 数据库使用读写分离和分片策略
- 对象存储使用 CDN 加速

## 安全性

### 认证和授权

- API 使用 JWT 认证（V1 占位）
- 基于角色的访问控制（RBAC）
- 审核操作需要特定权限

### 数据保护

- 敏感数据加密存储
- API 传输使用 HTTPS
- 定期备份数据库和对象存储
- 审计日志记录关键操作

### 输入验证

- 所有 API 输入使用 Pydantic 验证
- 文档内容使用 JSON Schema 验证
- 防止 SQL 注入和 XSS 攻击
- 限制文件上传大小和类型
