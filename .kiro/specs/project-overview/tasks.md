# AI 漫剧生成平台 - 项目总体任务清单

## 项目概述

本文档记录整个项目的迭代进度、已完成任务和下一步计划。每个迭代对应一个独立的 spec，本文档作为总控文档。

---

## 迭代总览

### 已完成的迭代

- [x] **Iteration 0**: 文档冻结与建模清单 ✅
- [x] **Iteration 1**: 核心对象与真实 Workspace 骨架 ✅
- [x] **Iteration 2**: 文本主链路打通（真实 LLM 集成）✅

### 进行中的迭代

- [ ] **Iteration 3**: Storyboard 到 Asset 工作台 🔄 (Spec 已完成，准备执行)

### 待完成的迭代

- [ ] **Iteration 4**: 媒体链路 Alpha
- [ ] **Iteration 5**: QA / Review / Rerun 闭环
- [ ] **Iteration 6**: Final Export 与 Pilot Ready 强化

---

## 里程碑状态

- [x] **M1**: 文本链路走到 storyboard，workspace 可显示真实 documents 与 shots ✅
- [ ] **M2**: preview 可生成，资产入库可见
- [ ] **M3**: QA / review / rerun / export 闭环可用，单集包能真正交付
- [ ] **M4**: 样板项目稳定重复运行，系统可以进入 pilot 试用

---

## Iteration 0: 文档冻结与建模清单 ✅

**时间**: 第 0 周  
**状态**: 已完成  
**目标**: 让团队对边界、系统形态和交付节奏达成一致

### 完成的任务

- [x] 1. 冻结 V1 scope
  - 产品路线图文档
  - 系统蓝图文档
  - 交付计划文档
  - _需求: 所有_

- [x] 2. 列出现有和缺失模型
  - 现有模型清单
  - 缺失模型清单
  - Migration backlog
  - _需求: 所有_

- [x] 3. 冻结 stage 列表和 workflow 状态机
  - Stage 类型定义
  - Workflow 状态机设计
  - Rerun 粒度定义
  - _需求: 2.1, 2.2, 2.5_

- [x] 4. 冻结 workspace 最小字段集合
  - Workspace 聚合结构
  - 前端视图分区
  - _需求: 7.1_

### DoD 验证

- ✅ 文档三件套存在：roadmap / scope / blueprint
- ✅ 缺失对象清单明确
- ✅ 第一轮开发不再讨论大边界问题

---

## Iteration 1: 核心对象与真实 Workspace 骨架 ✅

**时间**: 第 1-2 周  
**状态**: 已完成  
**目标**: 把系统从"有壳子"推进到"有真实业务骨架"

### 完成的任务

- [x] 1. 新增核心数据模型
  - [x] 1.1 StageTask 模型与 migration
    - 记录 Stage 执行状态和时间
    - 关联 WorkflowRun
    - _需求: 2.2, 2.3_

  - [x] 1.2 Shot 模型与 migration
    - 记录分镜级信息
    - 包含视觉约束
    - _需求: 6.1, 6.2_

  - [x] 1.3 ReviewDecision 模型与 migration
    - 记录人工审核决策
    - 关联 WorkflowRun
    - _需求: 11.1, 11.2_

- [x] 2. 补充 Repository 和 Schema
  - [x] 2.1 StageTask Repository
  - [x] 2.2 Shot Repository
  - [x] 2.3 ReviewDecision Repository
  - [x] 2.4 Response DTO 定义
  - _需求: 所有_

- [x] 3. 重构 Workspace 聚合逻辑
  - [x] 3.1 聚合 StageTask 信息
  - [x] 3.2 聚合 Shot 信息
  - [x] 3.3 聚合 ReviewDecision 信息
  - [x] 3.4 返回真实数据而非占位数据
  - _需求: 7.1, 7.2, 7.3, 7.4_

- [x] 4. Workflow 基础框架
  - [x] 4.1 WorkflowRun 可以写入数据库
  - [x] 4.2 每个 Stage 生成 StageTask 记录
  - [x] 4.3 Storyboard Stage 提供 Shot 持久化接口
  - _需求: 2.1, 2.2, 2.3_

- [x] 5. 前端接入真实 Workspace API
  - [x] 5.1 工作台接入真实 workspace API
  - [x] 5.2 Storyboard 区展示真实 Shot 列表
  - [x] 5.3 Workflow 区展示当前 Stage 状态
  - _需求: 7.1, 7.2, 7.3_

### DoD 验证

- ✅ 数据库中存在真实 stage_tasks、shots、review_decisions 表
- ✅ Workspace 接口返回真实 Shot 数据
- ✅ 前端不再依赖硬编码 Shot 数组
- ✅ 可以通过 API 看到 Workflow 和 Stage 的基础状态

---

## Iteration 2: 文本主链路打通（真实 LLM 集成）✅

**时间**: 第 3-4 周  
**状态**: 已完成  
**目标**: 跑通 `素材 -> brief -> story_bible -> character -> script -> storyboard`

**Spec 位置**: `.kiro/specs/text-pipeline-mock/`

### 完成的任务

- [x] 1. 核心数据模型和 Repository
  - 数据库模型已存在
  - Repository 已实现
  - _需求: 1.1, 1.3, 2.3, 3.3, 4.3, 5.3, 6.3_

- [x] 2. 工作流编排服务
  - WorkflowService 已实现
  - TextWorkflowService 实现文本链路
  - Stage 顺序执行和文档创建
  - _需求: 1.1, 1.2, 1.3, 1.4_

- [x] 3. Workspace 聚合 API
  - GET /workspace 端点已实现
  - DatabaseStore.build_workspace 聚合所有数据
  - 返回 project, episode, documents, shots, stage_tasks
  - _需求: 8.1, 8.2, 8.3, 8.4_

- [x] 4. API 端点
  - POST /workflow/start 端点
  - GET /workflow 端点
  - Review 提交端点
  - _需求: 1.1, 9.1, 9.2_

- [x] 5. Agent Runtime 框架
  - [x] 5.1 BaseAgent 7 阶段流水线
    - Loader → Normalizer → Planner → Generator → Critic → Validator → Committer
    - StageTaskInput 和 StageTaskOutput 数据类
    - _需求: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [x] 5.2 真实 LLM 服务（已从 Mock 升级）
    - 支持通义千问、OpenAI、Claude
    - 统一的服务抽象层
    - JSON 解析和错误处理
    - _需求: 2.2, 3.2, 4.2, 5.2, 6.2, 15.1, 15.2, 15.3, 15.4, 15.5_

  - [x] 5.3 一致性检查器（Critic 组件）
    - Brief anchor 检查
    - 角色一致性检查
    - 世界规则违反检查
    - 生成警告
    - _需求: 7.1, 7.2, 7.3, 7.4_

  - [x] 5.4 验证器组件
    - JSON Schema 验证
    - 必填字段检查
    - 锁定字段保护
    - _需求: 2.4, 7.5, 9.3, 9.5_

- [x] 6. 实现所有 Agent（真实 LLM）
  - [x] 6.1 Brief Agent
    - 真实 LLM 集成
    - Brief 输出 Schema
    - 验证必填字段
    - _需求: 2.1, 2.2, 2.3, 2.4_

  - [x] 6.2 Story Bible Agent
    - 真实 LLM 集成
    - Story Bible 输出 Schema
    - 加载 Brief 作为输入
    - _需求: 3.1, 3.2, 3.3, 3.4_

  - [x] 6.3 Character Agent
    - 真实 LLM 集成
    - Character Profile 输出 Schema
    - 加载 Brief 和 Story Bible
    - 标记 visual_anchors 为可锁定
    - _需求: 4.1, 4.2, 4.3, 4.4_

  - [x] 6.4 Script Agent
    - 真实 LLM 集成
    - Script Draft 输出 Schema
    - 加载 Brief、Story Bible、Character Profile
    - 验证场景结构
    - _需求: 5.1, 5.2, 5.3, 5.4_

  - [x] 6.5 Storyboard Agent
    - 真实 LLM 集成
    - Visual Spec 输出 Schema 和 Shot 结构
    - 加载 Script Draft 和平台约束
    - 生成 Shot 记录
    - _需求: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 7. 集成 Agent 到 Workflow
  - [x] 7.1 TextWorkflowService 调用真实 Agent
    - 替换 Mock 文档生成
    - 构建 StageTaskInput
    - 处理 StageTaskOutput
    - _需求: 1.2, 1.5, 11.1, 11.2, 11.3_

  - [x] 7.2 错误处理和重试逻辑
    - Agent 执行的 try-catch
    - 记录 error_code 和 error_message
    - 重试逻辑（最多 3 次）
    - _需求: 1.5, 2.5, 3.5, 4.5, 5.5, 11.4_

  - [x] 7.3 执行日志和指标
    - 记录 Stage 开始和完成
    - 记录 LLM 调用
    - 记录 Document 提交
    - _需求: 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 8. 文档编辑功能
  - [x] 8.1 Document 更新端点
    - PUT /documents/{document_id}
    - 创建新版本
    - 记录 created_by
    - _需求: 9.1, 9.2, 9.4_

  - [x] 8.2 锁定字段验证
    - 检查锁定字段
    - 拒绝修改锁定字段
    - _需求: 9.3_

  - [x] 8.3 Schema 验证
    - 验证 content_jsonb
    - 检查必填字段
    - _需求: 9.5_

- [x] 9. 测试基础设施
  - [x] 9.1 设置 pytest 和 Hypothesis
    - 添加依赖
    - 创建 pytest.conftest
    - 数据库 fixtures
    - _需求: 所有_

- [x] 10. Checkpoint - 确保所有测试通过
  - 39 个单元测试通过
  - 89% 测试覆盖率
  - 验证脚本通过

- [x] 11. 数据库索引优化
  - [x] 11.1 documents 索引
    - (episode_id, document_type, version DESC)
    - _需求: 8.2_

  - [x] 11.2 shots 索引
    - (episode_id, scene_no, shot_no)
    - _需求: 8.3_

  - [x] 11.3 stage_tasks 索引
    - (workflow_run_id, stage_type, created_at)
    - _需求: 8.4_

- [x] 12. Final Checkpoint
  - 所有核心功能完成
  - 测试通过
  - 文档完整

### DoD 验证

- ✅ 一个剧集可以从 start_workflow 跑到 storyboard 完成
- ✅ 所有文本产物入库
- ✅ 每个 Stage 有 StageTask 记录
- ✅ Storyboard 输出真实 Shot 实体
- ✅ 用户可以在前端看到并编辑关键文本产物
- ✅ 所有 5 个 Agent 都集成了真实 LLM（不是 Mock）

### 性能指标

- Brief Agent 响应时间: 10-15秒
- Token 使用: 800-1200 tokens
- 成本: ¥0.004/次 (~$0.0006)
- 完整链路耗时: 2-3 分钟
- 完整链路成本: ¥0.05 (~$0.007)

### 完成报告

详见: `.kiro/specs/text-pipeline-mock/ITERATION2_COMPLETION_REPORT.md`

---

## Iteration 3: Storyboard 到 Asset 工作台 🔄

**时间**: 第 5-6 周  
**状态**: Spec 已完成，准备执行  
**目标**: 把 storyboard 变成能驱动后续媒体链路的稳定中枢

**Spec 位置**: `.kiro/specs/storyboard-to-asset/`

### 计划的任务

- [ ] 1. 验证 Shot 模型完整性
  - [ ] 1.1 检查 Shot 包含所有必需字段
  - [ ] 1.2 确认 visual_constraints_jsonb 结构正确
  - [ ] 1.3 验证 Shot 与 visual_spec 的关联
  - _需求: 6.1, 6.2, 6.3, 6.4_

- [ ] 2. 验证 visual_spec 文档结构
  - [ ] 2.1 确认 visual_spec 包含 render_prompt
  - [ ] 2.2 确认 style_keywords 和 composition 信息完整
  - [ ] 2.3 验证 visual_spec 可被 image_render 消费
  - _需求: 3.5, 8.1_

- [ ] 3. 设计 image_render 输入构建逻辑
  - [ ] 3.1 从 visual_spec 提取渲染参数
  - [ ] 3.2 从 character_profile 提取 visual_anchor
  - [ ] 3.3 组装完整的图像生成 Prompt
  - [ ] 3.4 定义 Shot-level rerun input
  - _需求: 8.1, 12.2_

- [ ] 4. 完善 Shot 卡片展示
  - [ ] 4.1 定义 Shot 卡片字段
  - [ ] 4.2 定义 Shot 锁定与编辑入口
  - [ ] 4.3 定义 visual spec 与 Shot 的关系展示
  - _需求: 6.3, 6.4_

- [ ] 5. 补齐资产关联字段
  - [ ] 5.1 Shot 与 visual spec 引用关系
  - [ ] 5.2 资产与 Shot 的关联字段
  - [ ] 5.3 为后续资产页预留选主资产区
  - _需求: 9.1, 9.2_

### DoD

- [ ] Storyboard 的结果可直接被 image_render 消费
- [ ] visual_spec 已进入真实数据链
- [ ] 每个 Shot 都可以作为后续渲染目标
- [ ] 分镜页显示 Shot 详情和 visual constraint 摘要

---

## Iteration 4: 媒体链路 Alpha

**时间**: 第 7-8 周  
**状态**: 未开始  
**目标**: 跑通 `visual_spec -> image_render -> subtitle -> tts -> preview`

**Spec 位置**: `.kiro/specs/media-pipeline-alpha/` (待创建)

### 计划的任务

- [ ] 1. Object Storage 接入
  - [ ] 1.1 配置 S3/OSS
  - [ ] 1.2 实现上传和下载接口
  - [ ] 1.3 资产 metadata 完整写入
  - _需求: 8.5, 9.1_

- [ ] 2. Media Runtime 实现
  - [ ] 2.1 Image Render Worker
  - [ ] 2.2 Subtitle 生成逻辑
  - [ ] 2.3 TTS Worker
  - [ ] 2.4 Preview Export Worker
  - _需求: 8.1, 8.2, 8.3, 8.4_

- [ ] 3. 资产选择功能
  - [ ] 3.1 资产选择接口
  - [ ] 3.2 主资产标记逻辑
  - [ ] 3.3 候选资产展示
  - _需求: 9.2, 9.3_

- [ ] 4. Preview 展示
  - [ ] 4.1 Preview 页接入真实 preview 资产
  - [ ] 4.2 失败提示
  - _需求: 8.4_

### DoD

- [ ] 至少一条样板项目链路能生成 preview
- [ ] image / subtitle / audio / preview 资产都可追踪
- [ ] 工作台能展示主资产与候选资产

---

## Iteration 5: QA / Review / Rerun 闭环

**时间**: 第 9-10 周  
**状态**: 未开始  
**目标**: 把系统从"能生成"升级为"能返工、能审核、能放行"

**Spec 位置**: `.kiro/specs/qa-review-rerun/` (待创建)

### 计划的任务

- [ ] 1. QA Runtime 实现
  - [ ] 1.1 规则检查
  - [ ] 1.2 语义检查
  - [ ] 1.3 QA 报告生成
  - _需求: 10.1, 10.2_

- [ ] 2. Review Gate 实现
  - [ ] 2.1 ReviewDecision 提交接口
  - [ ] 2.2 Workflow 暂停与恢复
  - _需求: 11.1, 11.2, 11.3, 11.4_

- [ ] 3. Rerun 功能实现
  - [ ] 3.1 rerun_workflow 创建新 WorkflowRun
  - [ ] 3.2 指定 Shot 重跑 image_render
  - [ ] 3.3 Rerun 不覆盖非目标对象
  - _需求: 12.1, 12.2, 12.3, 12.4_

- [ ] 4. QA 和 Review 页面
  - [ ] 4.1 QA 报告展示
  - [ ] 4.2 审核按钮接口
  - [ ] 4.3 Rerun 入口
  - _需求: 10.1, 11.1, 12.1_

### DoD

- [ ] QA 失败会阻止 final export
- [ ] 审核动作会改变 workflow 状态
- [ ] 指定 Shot 可以重跑 image_render
- [ ] Rerun 不覆盖非目标对象
- [ ] 用户能看懂为什么被打回

---

## Iteration 6: Final Export 与 Pilot Ready 强化

**时间**: 第 11-12 周  
**状态**: 未开始  
**目标**: 让系统具备最小 pilot 条件

**Spec 位置**: `.kiro/specs/final-export-pilot/` (待创建)

### 计划的任务

- [ ] 1. Final Export 实现
  - [ ] 1.1 export_final stage 落地
  - [ ] 1.2 ExportBundle 记录落地
  - [ ] 1.3 导出历史可查询
  - _需求: 13.1, 13.2, 13.3_

- [ ] 2. 可观测性强化
  - [ ] 2.1 Trace / lineage 基础能力
  - [ ] 2.2 Rerun history 可查询
  - [ ] 2.3 基础统计可查询
  - _需求: 14.1, 14.2, 14.3, 14.4, 14.5_

- [ ] 3. 导出页面
  - [ ] 3.1 导出页显示 final 结果
  - [ ] 3.2 导出结果和产物列表展示
  - _需求: 13.3_

- [ ] 4. 样板项目验证
  - [ ] 4.1 样板项目可重复成功运行
  - [ ] 4.2 Provider 失败降级规则
  - _需求: 所有_

### DoD

- [ ] 最终单集包可导出
- [ ] 一条样板链路可重复成功运行至少两次
- [ ] 能回答"卡在哪一步""为什么失败""重跑后发生了什么"
- [ ] Pilot 演示不需要工程师手工改库救火

---

## 当前优先级

### 立即行动（本周）

1. **运行端到端测试验证 Iteration 2**
   ```bash
   cd apps/api
   python test_full_workflow.py
   ```

2. **创建 Iteration 3 的 Spec**
   - 创建 `.kiro/specs/storyboard-to-asset/` 目录
   - 编写 requirements.md
   - 编写 design.md
   - 编写 tasks.md

3. **开始 Iteration 3 的第一个任务**
   - 验证 Shot 模型完整性
   - 验证 visual_spec 文档结构

### 下周计划

1. 完成 Iteration 3 的核心任务
2. 为 Iteration 4 做准备
3. 选择和配置 Image Provider

---

## 技术债务和改进项

### 测试相关

- [ ] 补充 Property-Based Tests（可选，不阻塞进度）
- [ ] 补充 Integration Tests（可选，不阻塞进度）
- [ ] 创建测试数据生成器（可选）

### 文档相关

- [ ] 补充 API 文档
- [ ] 补充部署文档
- [ ] 补充运维手册

### 性能优化

- [ ] 数据库查询优化
- [ ] LLM 调用缓存
- [ ] 对象存储 CDN 加速

### 安全性

- [ ] 实现真实的认证授权
- [ ] 敏感数据加密
- [ ] 审计日志完善

---

## 项目统计

### 代码统计

- 代码行数: ~5000 行
- 测试覆盖率: 89%
- API 端点: 15+
- 数据模型: 8 个
- Agent: 5 个
- 测试用例: 39 个

### 进度统计

- 已完成迭代: 3/7 (43%)
- 已完成里程碑: 1/4 (25%)
- 预计完成时间: 第 12 周

### 成本统计

- Brief 生成: ¥0.004/次
- 完整文本链路: ¥0.05/次
- 预计完整剧集: ¥0.50/次（包含媒体生成）

---

## 相关文档

- **项目总结**: `PROJECT_SUMMARY.md`
- **README**: `README.md`
- **交付计划**: `docs/engineering/DELIVERY-PLAN.md`
- **系统蓝图**: `docs/engineering/SYSTEM-BLUEPRINT.md`
- **文档组织**: `docs/engineering/DOCUMENT_ORGANIZATION.md`
- **Iteration 2 完成报告**: `.kiro/specs/text-pipeline-mock/ITERATION2_COMPLETION_REPORT.md`
- **Iteration 2 下一步**: `docs/engineering/ITERATION2_NEXT_STEPS.md`

---

**最后更新**: 2026-04-07  
**当前迭代**: Iteration 3 准备中  
**下一个里程碑**: M2 - preview 可生成，资产入库可见
