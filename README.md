# AI 漫剧创作者工作台

[English](./README.en.md) | 简体中文

> 面向短视频平台（抖音、快手）的 AI 驱动漫剧生产平台，将网文小说转化为竖屏漫剧分镜脚本。

## 🎯 项目概述

这是一个全栈 AI 生产平台，通过编排多个专业化 AI Agent 来自动化从原始素材到分镜脚本的创作流程。系统展示了先进的工作流编排、Agent 架构和生产级软件工程实践。

**目标场景**：将中文网络小说（特别是女频言情/逆袭题材）转化为结构化的竖屏短视频分镜脚本。

## 🏗️ 架构亮点

### 系统设计原则

1. **Workflow-First 架构**：业务逻辑由显式的工作流编排驱动，而非隐式的 Agent 链式调用
2. **Artifact-First 状态管理**：系统状态源自结构化产物（文档、镜头），而非聊天上下文
3. **运行时分离**：文本生成（Agent）、编排（Workflow）、持久化（Repository）职责清晰分离
4. **显式状态建模**：所有状态显式建模，可追踪、可回滚
5. **防偏移机制**：多层一致性检查防止内容偏离原始创意方向

### 技术栈

**后端**:
- Python 3.8+ with FastAPI
- PostgreSQL 16（主数据存储）
- SQLAlchemy 2.0（ORM，支持异步）
- Temporal（工作流编排 - 计划中）
- Redis（缓存和会话管理）

**前端**:
- Next.js 14 with TypeScript
- React 18 with Server Components
- TailwindCSS（样式）
- Radix UI（无障碍组件）

**基础设施**:
- Docker & Docker Compose
- MinIO（S3 兼容对象存储）
- Alembic（数据库迁移）

**测试**:
- pytest with pytest-asyncio
- Hypothesis（基于属性的测试）
- 核心服务 89% 测试覆盖率

## 📐 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                          API 层                                 │
│  POST /workflow/start  │  GET /workspace  │  PUT /documents    │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────────────────────────┐
│                   工作流编排器                                   │
│  • Episode 工作流状态机                                          │
│  • Stage 任务输入构建器                                          │
│  • 重试与失败处理                                                │
│  • 执行日志与指标                                                │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────────────────────────┐
│                      Agent 运行时                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Brief Agent  │  │ Story Bible  │  │  Character   │         │
│  │  创意简报    │  │   世界观     │  │   角色设定   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐                           │
│  │ Script Agent │  │  Storyboard  │                           │
│  │   剧本生成   │  │   分镜生成   │                           │
│  └──────────────┘  └──────────────┘                           │
│                                                                 │
│  通用流水线: Loader → Normalizer → Planner →                   │
│             Generator → Critic → Validator → Committer         │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────────────────────────┐
│                      数据层                                     │
│  PostgreSQL: projects, episodes, workflow_runs, stage_tasks,    │
│              documents, shots                                   │
│  Repositories: ProjectRepo, EpisodeRepo, WorkflowRepo,          │
│                DocumentRepo, ShotRepo, StageTaskRepo            │
└─────────────────────────────────────────────────────────────────┘
```

## 🤖 Agent 流水线架构

每个 Agent 遵循标准化的 7 阶段流水线：

```python
class BaseAgent:
    def execute(self, task_input: StageTaskInput) -> StageTaskOutput:
        # 1. Loader: 加载输入文档和引用
        context = self.loader.load(task_input.input_refs, task_input.locked_refs)
        
        # 2. Normalizer: 清洗和结构化上下文
        normalized = self.normalizer.normalize(context, task_input.constraints)
        
        # 3. Planner: 创建执行计划
        plan = self.planner.build(normalized, task_input.stage_type)
        
        # 4. Generator: 调用 LLM 生成内容
        draft = self.generator.generate(plan, schema=self.output_schema)
        
        # 5. Critic: 自我审查一致性
        reviewed = self.critic.review(draft, normalized)
        
        # 6. Validator: 验证 schema 和约束
        valid = self.validator.validate(reviewed, task_input.locked_refs)
        
        # 7. Committer: 持久化到数据库
        refs = self.committer.commit(valid, task_input.project_id, task_input.episode_id)
        
        return StageTaskOutput(...)
```

### Agent 专业化分工

1. **Brief Agent（创意简报）**: 从原始素材提取核心创意方向
   - 输入：原始小说片段、平台约束、目标受众
   - 输出：题材类型、卖点、主要冲突、改编策略

2. **Story Bible Agent（世界观）**: 建立世界规则和约束
   - 输入：Brief、素材摘要
   - 输出：世界规则、时间线、禁止冲突、关键设定

3. **Character Agent（角色设定）**: 定义角色档案和视觉锚点
   - 输入：Brief、Story Bible
   - 输出：角色档案（性格、目标、视觉描述）

4. **Script Agent（剧本生成）**: 生成逐场景剧本和对白
   - 输入：Brief、Story Bible、Character 档案
   - 输出：结构化场景（对白、情绪节拍、时长）

5. **Storyboard Agent（分镜生成）**: 创建镜头级规格说明
   - 输入：Script、平台约束
   - 输出：镜头记录（机位、构图、视觉提示）

## 🔄 工作流编排

工作流服务实现了一个状态机，负责：

- **构建阶段输入**：构造带有正确文档引用和约束的 `StageTaskInput`
- **处理 Agent 输出**：处理 `StageTaskOutput` 并决定下一步动作
- **管理失败**：实现重试逻辑（最多 3 次尝试）和指数退避
- **保留产物**：失败时保留所有中间产物以便恢复
- **追踪执行**：记录阶段开始/完成、时长、token 使用量和错误

### 失败隔离

每个阶段的失败都是隔离的：
- Brief 失败 → 对项目无影响
- Story Bible 失败 → Brief 保持完整
- Character 失败 → Brief 和 Story Bible 保持完整
- Script 失败 → 保护旧版本，上游文档完整
- Storyboard 失败 → Script 和所有上游文档完整

## 📊 数据模型

### 核心实体

**WorkflowRun（工作流运行）**: 追踪端到端工作流执行
- 状态：created → running → succeeded/failed
- 链接到 Temporal 工作流（用于分布式执行）
- 支持从特定阶段重新运行

**StageTask（阶段任务）**: 表示单个 Agent 执行
- 追踪输入/输出引用
- 记录重试次数和错误
- 支持人工审核关卡

**Document（文档）**: 版本化的结构化内容
- 类型特定的 JSON schema（brief、story_bible、character_profile 等）
- 版本历史和创建者追踪（AI vs 人工）
- 可锁定字段防止下游偏移

**Shot（镜头）**: 分镜的原子视觉单元
- 机位规格（景别、角度、运动）
- 角色引用和视觉约束
- 时长和排序信息

## 🧪 测试策略

### 单元测试（39 个通过）

- **服务层**：工作流编排、文档验证、审核逻辑
- **Repository 层**：CRUD 操作、版本管理、查询方法
- **Agent 流水线**：各流水线阶段隔离、错误传播

### 基于属性的测试（框架就绪）

使用 Hypothesis 进行 PBT，每个属性测试 100+ 次迭代：

- **工作流属性**：阶段顺序保持、失败时产物隔离
- **文档属性**：必填字段验证、版本递增正确性
- **一致性属性**：Brief 对齐、角色行为一致性、世界规则遵守
- **工作区属性**：完整聚合、最新版本选择

示例属性测试：
```python
@given(st.text(min_size=1), st.integers(min_value=1))
def test_document_version_increment(content, current_version):
    """对于任何文档编辑，版本号应该恰好递增 1"""
    new_doc = edit_document(content, current_version)
    assert new_doc.version == current_version + 1
```

## 🔍 关键技术决策

### 1. Workflow-First vs Agent-First

**决策**：工作流编排器控制执行流程，Agent 是无状态工作者。

**理由**：
- 实现集中式重试逻辑和失败处理
- 允许工作流暂停等待人工审核
- 使执行可追踪、可调试
- 支持从任意阶段部分重跑

### 2. Artifact-First 状态管理

**决策**：系统状态源自结构化文档，而非聊天历史。

**理由**：
- 文档有版本且可审计
- 状态可从产物重建
- 支持回滚和分支
- 支持独立阶段的并行执行

### 3. 一致性 Critic 模式

**决策**：每个 Agent 包含自我审查的 "Critic" 阶段检查一致性。

**理由**：
- 在持久化前及早捕获偏移
- 为人工审核生成可操作的警告
- 不阻塞执行（警告而非错误）
- 为下游阶段提供质量信号

### 4. 锁定字段保护

**决策**：关键字段（角色名、视觉锚点、核心冲突）可被锁定。

**理由**：
- 防止下游 Agent 更改已确立的事实
- 支持迭代优化而不破坏一致性
- 支持必须保留的人工编辑
- 实现"创意锚点"模式

## 📁 项目结构

```
.
├── apps/
│   ├── api/                    # FastAPI 后端
│   │   ├── app/
│   │   │   ├── api/           # API 路由
│   │   │   ├── db/            # 数据库模型
│   │   │   ├── repositories/  # 数据访问层
│   │   │   ├── schemas/       # Pydantic schemas
│   │   │   └── services/      # 业务逻辑
│   │   └── tests/             # 单元和集成测试
│   └── web/                   # Next.js 前端
├── workers/
│   ├── agent-runtime/         # AI Agent 实现
│   │   ├── base_agent.py     # 通用流水线
│   │   ├── brief_agent.py    # Brief 生成
│   │   ├── story_bible_agent.py
│   │   ├── character_agent.py
│   │   ├── script_agent.py
│   │   └── storyboard_agent.py
│   ├── media-runtime/         # 图像/视频生成
│   └── qa-runtime/            # 质量保证
├── infra/
│   ├── docker/                # Docker Compose 配置
│   ├── migrations/            # Alembic 迁移
│   └── temporal/              # Temporal 工作流
├── docs/
│   ├── product/               # 产品规格和 PRD
│   ├── design/                # 设计系统
│   ├── engineering/           # 技术文档
│   └── interview/             # 面试准备材料
└── .kiro/specs/               # 功能规格说明
```

## 🚀 快速开始

### 前置要求

- Python 3.8+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 16（通过 Docker）

### 启动步骤

1. **启动基础设施**：
```bash
cd infra/docker
docker-compose up -d postgres redis minio
```

2. **设置 Python 环境**：
```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. **运行数据库迁移**：
```bash
cd infra/migrations
alembic upgrade head
```

4. **运行测试**：
```bash
cd apps/api
pytest tests/ -v
```

5. **启动 API 服务器**：
```bash
cd apps/api
uvicorn app.main:app --reload --port 8000
```

6. **启动前端**（新终端）：
```bash
cd apps/web
npm install
npm run dev
```

访问应用：`http://localhost:3000`

## 📈 当前状态

**已完成**：
- ✅ 核心数据模型和 Repository
- ✅ 工作流编排服务
- ✅ 全部 5 个文本 Agent（Brief、Story Bible、Character、Script、Storyboard）
- ✅ Agent 流水线框架（7 阶段执行）
- ✅ 文档验证和锁定字段保护
- ✅ 工作区聚合 API
- ✅ 一致性检查（Critic 组件）
- ✅ 错误处理和重试逻辑
- ✅ 执行日志和指标
- ✅ 单元测试套件（39 个测试通过）
- ✅ 基于属性的测试框架搭建

**进行中**：
- 🔄 真实数据库集成测试
- 🔄 前端工作区 UI
- 🔄 Temporal 工作流集成

**计划中**：
- 📋 媒体生成 Agent（图像、视频）
- 📋 QA Agent 质量保证
- 📋 人工审核 UI
- 📋 资产管理系统

## 🎓 技术亮点

本项目展示了：

1. **分布式系统**：工作流编排、状态管理、失败处理
2. **AI 工程**：多 Agent 协作、提示工程、一致性检查
3. **软件架构**：整洁架构、Repository 模式、依赖注入
4. **测试**：单元测试、基于属性的测试、测试驱动开发
5. **数据库设计**：版本控制、软删除、审计追踪、索引策略
6. **API 设计**：RESTful API、请求/响应 schema、错误处理
7. **DevOps**：Docker 容器化、数据库迁移、环境管理

## 📚 文档

- **产品规格**：`docs/product/` - 产品愿景、MVP 计划、PRD
- **技术文档**：`docs/engineering/` - API 契约、Agent 架构、工作流设计
- **设计系统**：`docs/design/` - UI 组件、设计 token、风格指南
- **功能规格**：`.kiro/specs/` - 详细功能需求和设计文档

## 📄 许可证

本项目仅用于技术展示和学习交流，不用于商业用途。

---

**最后更新**：2026 年 4 月
